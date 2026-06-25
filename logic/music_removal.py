import gc
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import torch
from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal
from audio_separator.separator import Separator

from config import MessageType, DEFAULT_MODEL, CHUNKING
from .benchmarking import BenchmarkRecorder
from .utils import get_temp_path, get_resource_path


class StreamCatcher:
    def __init__(self, signal, original_stderr):
        self.signal = signal
        self.original_stderr = original_stderr
        self.regex = re.compile(r"(\d{1,3})%")

    def write(self, text):
        self.original_stderr.write(text)
        match = self.regex.search(text)
        if match:
            percent = float(match.group(1))
            self.signal.emit(percent)

    def flush(self):
        self.original_stderr.flush()


class MusicRemoverThread(QThread):
    progress: pyqtBoundSignal = pyqtSignal(str, MessageType)
    progress_percent: pyqtBoundSignal = pyqtSignal(float)
    completed: pyqtBoundSignal = pyqtSignal(bool)

    def __init__(
        self,
        input_video: Path,
        user_output: Path,
        gpu_enabled: bool = True,
        use_tensorrt: bool = False,
        gpu_threads: int = 1,
        chunking_enabled: bool = True,
        chunk_secs: int = 60,
        cpu_threads: int = 2,
        retry_failed_chunks: bool = True,
        benchmark_recorder: BenchmarkRecorder | None = None,
        source_type: str = "file",
        overall_start: float | None = None,
    ) -> None:
        super().__init__()
        self.input_video: Path = input_video
        self.user_output: Path = user_output
        self.temp_parent: Path = get_temp_path()
        self.gpu_enabled: bool = gpu_enabled
        self.use_tensorrt: bool = use_tensorrt
        self.gpu_threads: int = gpu_threads
        self.chunking_enabled: bool = chunking_enabled
        self.chunk_secs: int = chunk_secs
        self.cpu_threads: int = cpu_threads
        self.retry_failed_chunks: bool = retry_failed_chunks

        self.base_name: str = self.input_video.stem
        self.temp_dir: Path = self.temp_parent / self.base_name
        self.output_audio: Path = self.temp_dir / f"{self.base_name}_AUDIO.wav"
        self.output_video: Path = self.temp_dir / f"{self.base_name}_VIDEO.mp4"
        self.final_audio_path: Path = Path()
        self._benchmark_recorder: BenchmarkRecorder | None = benchmark_recorder
        self._source_type: str = source_type
        self._overall_start: float | None = overall_start

    def run(self) -> None:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_audio = self.temp_dir / f"{self.base_name}_AUDIO.wav"
        self.output_video = self.temp_dir / f"{self.base_name}_VIDEO.mp4"
        total_start = time.monotonic()

        try:
            self._split()
        except (RuntimeError, OSError):
            self._finalize_benchmark(False)
            self.completed.emit(False)
            return

        if self._benchmark_recorder:
            from logic.ffmpeg_utils import get_audio_duration

            dur = get_audio_duration(self.output_audio)
            self._benchmark_recorder.set_video_info(
                source_type=self._source_type,
                filename=self.input_video.name,
                duration_sec=dur,
            )
            self._benchmark_recorder.set_file_size("input", self.input_video)
            self._benchmark_recorder.set_file_size("audio", self.output_audio)
            mins = int(dur // 60)
            secs = int(dur % 60)
            self.progress.emit(f"Duration: {mins}m {secs}s", MessageType.PROGRESS)

        try:
            wav_size_mb = self.output_audio.stat().st_size / (1024 * 1024)
            use_chunking = (
                self.chunking_enabled and wav_size_mb > CHUNKING["threshold_mb"]
            )

            if use_chunking:
                self._process_chunked()
            else:
                self._process_normal()
        except Exception:
            self._finalize_benchmark(False)
            self.completed.emit(False)
            return

        try:
            self._combine()
            pipeline_elapsed = time.monotonic() - total_start
            if self._benchmark_recorder:
                self._benchmark_recorder.set_pipeline_time(pipeline_elapsed)
                self._benchmark_recorder.set_file_size(
                    "output", self.user_output / self.output_video.name
                )
                self.progress.emit(
                    f"Pipeline: {pipeline_elapsed:.1f}s", MessageType.PROGRESS
                )
                if self._overall_start is not None:
                    overall_elapsed = time.monotonic() - self._overall_start
                    self._benchmark_recorder.set_overall_time(overall_elapsed)
                    self.progress.emit(
                        f"Total: {overall_elapsed:.1f}s", MessageType.PROGRESS
                    )
            self._finalize_benchmark(True)
            self.completed.emit(True)
        except (RuntimeError, OSError):
            self._finalize_benchmark(False)
            self.completed.emit(False)

    def _split(self) -> None:
        from logic.ffmpeg_utils import split_video

        self.progress.emit(f"Splitting {self.input_video}", MessageType.DEBUG)
        split_start = time.monotonic()
        try:
            split_video(self.input_video, self.output_audio, self.output_video)
        except (RuntimeError, OSError) as e:
            self.progress.emit("Splitting Error: " + str(e), MessageType.ERROR)
            raise
        split_elapsed = time.monotonic() - split_start

        if self._benchmark_recorder:
            self.progress.emit(f"Split: {split_elapsed:.1f}s", MessageType.PROGRESS)
            self._benchmark_recorder.set_phase_time("split", split_elapsed)

    def _make_separator(self) -> Separator:
        use_gpu = self.gpu_enabled and torch.cuda.is_available()

        if use_gpu:
            provider = "TensorRT" if self.use_tensorrt else "CUDA"
            self.progress.emit(
                f"GPU acceleration enabled ({provider}): {torch.cuda.get_device_name(0)}",
                MessageType.DEBUG,
            )

        model_dir = get_resource_path(".models")
        self.progress.emit(
            f"Model dir: {model_dir} (exists: {model_dir.exists()}, frozen: {hasattr(sys, '_MEIPASS')})",
            MessageType.DEBUG,
        )

        separator = Separator(
            output_dir=str(self.temp_dir),
            model_file_dir=str(model_dir),
            use_autocast=use_gpu,
        )
        if not use_gpu:
            separator.onnx_execution_provider = ["CPUExecutionProvider"]
        elif self.use_tensorrt:
            separator.onnx_execution_provider = [
                "TensorrtExecutionProvider",
                "CUDAExecutionProvider",
            ]
        separator.load_model(DEFAULT_MODEL)
        return separator

    def _process_normal(self) -> None:
        separator = self._make_separator()

        self.progress.emit(
            f"Removing music from {self.input_video.name}", MessageType.INFO
        )

        original_stderr = sys.stderr
        catcher = StreamCatcher(self.progress_percent, original_stderr)
        sys.stderr = catcher

        process_start = time.monotonic()
        try:
            output_files = list(separator.separate(str(self.output_audio)))
        except Exception as e:
            self.progress.emit("Music Removal Error: " + str(e), MessageType.ERROR)
            raise
        finally:
            sys.stderr = original_stderr

        if self.output_audio.exists():
            self.output_audio.unlink()

        process_elapsed = time.monotonic() - process_start

        self.final_audio_path = self.temp_dir / Path(output_files[1])

        if self._benchmark_recorder:
            self.progress.emit(
                f"Remove music: {process_elapsed:.1f}s",
                MessageType.PROGRESS,
            )
            self._benchmark_recorder.set_phase_time("processing", process_elapsed)
            self._benchmark_recorder.set_file_size("clean_audio", self.final_audio_path)

    def _process_one_chunk(
        self, idx: int, chunk_path: Path, separator: Separator | None = None
    ) -> tuple[int, Path, list]:
        """Process a single audio chunk through the separator."""
        if not chunk_path.exists():
            raise FileNotFoundError(
                f"Chunk {idx + 1} file missing before separation: {chunk_path}"
            )
        sep = separator or self._make_separator()
        try:
            output = list(sep.separate(str(chunk_path)))
        except Exception as e:
            raise RuntimeError(f"Separator failed for chunk {idx + 1}: {e}") from e
        finally:
            if separator is None:
                del sep
        if len(output) < 2:
            raise RuntimeError(
                f"Chunk {idx + 1}: separator returned {len(output)} outputs (expected 2). "
                f"Model may have failed to load."
            )
        return idx, chunk_path, output

    def _run_chunks(
        self,
        chunk_indices: list[int],
        chunk_paths: list[Path],
        processed: list[Path | None],
        max_workers: int,
        total_for_progress: int,
    ) -> list[tuple[int, Exception]]:
        """Run chunks sequentially or in parallel. Returns list of (index, error) tuples."""
        errors: list[tuple[int, Exception]] = []

        if max_workers <= 1:
            sep = self._make_separator()
            try:
                for i, (idx, chunk_path) in enumerate(zip(chunk_indices, chunk_paths)):
                    try:
                        _, _, output = self._process_one_chunk(
                            idx, chunk_path, separator=sep
                        )
                        processed[idx] = self.temp_dir / Path(output[1])
                        chunk_path.unlink(missing_ok=True)
                    except Exception as e:
                        errors.append((idx, e))
                        self.progress.emit(
                            f"Chunk {idx + 1} Error: {e}", MessageType.ERROR
                        )
                    self.progress_percent.emit(int((i + 1) / total_for_progress * 100))
            finally:
                del sep
        else:
            old_omp = os.environ.get("OMP_NUM_THREADS")
            old_ort = os.environ.get("ORT_INTRA_OP_NUM_THREADS")
            old_torch = torch.get_num_threads()
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["ORT_INTRA_OP_NUM_THREADS"] = "1"
            torch.set_num_threads(1)
            try:
                thread_local = threading.local()

                def _get_thread_separator():
                    if not hasattr(thread_local, "sep"):
                        thread_local.sep = self._make_separator()
                    return thread_local.sep

                def _process_chunk(idx, ch):
                    return self._process_one_chunk(
                        idx, ch, separator=_get_thread_separator()
                    )

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(_process_chunk, idx, ch): idx
                        for idx, ch in zip(chunk_indices, chunk_paths)
                    }
                    completed_count = 0
                    for future in as_completed(futures):
                        idx = futures[future]
                        try:
                            _, chunk_path, output = future.result()
                            processed[idx] = self.temp_dir / Path(output[1])
                            chunk_path.unlink(missing_ok=True)
                        except Exception as e:
                            errors.append((idx, e))
                            self.progress.emit(
                                f"Chunk {idx + 1} Error: {e}", MessageType.ERROR
                            )
                        completed_count += 1
                        self.progress_percent.emit(
                            int(completed_count / total_for_progress * 100)
                        )
            finally:
                if old_omp is not None:
                    os.environ["OMP_NUM_THREADS"] = old_omp
                else:
                    os.environ.pop("OMP_NUM_THREADS", None)
                if old_ort is not None:
                    os.environ["ORT_INTRA_OP_NUM_THREADS"] = old_ort
                else:
                    os.environ.pop("ORT_INTRA_OP_NUM_THREADS", None)
                torch.set_num_threads(old_torch)

        return errors

    def _process_chunked(self) -> None:
        from logic.ffmpeg_utils import (
            combine_audio_chunks,
            get_audio_duration,
            split_audio_chunks,
        )

        total_dur = get_audio_duration(self.output_audio)
        total_chunks = max(1, int(total_dur // self.chunk_secs) + 1)

        self.progress.emit(
            f"Splitting audio into {total_chunks} chunks ({self.chunk_secs}s each)...",
            MessageType.DEBUG,
        )

        chunks = split_audio_chunks(
            self.output_audio,
            self.chunk_secs,
            CHUNKING["context_secs"],
        )

        missing = [c for c in chunks if not c.exists()]
        if missing:
            raise RuntimeError(
                f"Chunk files missing after split: {[str(c) for c in missing]}"
            )
        self.progress.emit(
            f"Created {len(chunks)} chunk files, all verified on disk.",
            MessageType.DEBUG,
        )

        max_workers = self.cpu_threads
        if self.gpu_enabled and torch.cuda.is_available():
            max_workers = self.gpu_threads

        self.progress.emit(
            f"Processing {len(chunks)} chunks ({max_workers} thread{'s' if max_workers > 1 else ''})...",
            MessageType.DEBUG,
        )

        processed: list[Path | None] = [None] * len(chunks)
        process_start = time.monotonic()

        indices = list(range(len(chunks)))
        errors = self._run_chunks(indices, chunks, processed, max_workers, len(chunks))

        if errors and self.retry_failed_chunks:
            retry_indices = [idx for idx, _ in errors]
            retry_chunks = [chunks[idx] for idx in retry_indices]
            self.progress.emit(
                f"Retrying {len(retry_indices)} failed chunk(s)...",
                MessageType.WARNING,
            )
            errors = self._run_chunks(
                retry_indices, retry_chunks, processed, max_workers, len(retry_indices)
            )

        if errors:
            for p in processed:
                if p is not None and p.exists():
                    p.unlink(missing_ok=True)
            failed_indices = [idx + 1 for idx, _ in errors]
            raise RuntimeError(f"{len(errors)} chunk(s) failed: {failed_indices}")

        processed_paths = [p for p in processed if p is not None]

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.progress.emit(
            f"Stitching {len(processed_paths)} chunks together...",
            MessageType.DEBUG,
        )

        final_clean = self.temp_dir / f"{self.base_name}_CLEAN.wav"
        combine_audio_chunks(
            processed_paths,
            CHUNKING["context_secs"],
            final_clean,
        )

        for c in processed_paths:
            c.unlink(missing_ok=True)

        if self.output_audio.exists():
            self.output_audio.unlink()

        process_elapsed = time.monotonic() - process_start

        self.final_audio_path = final_clean

        if self._benchmark_recorder:
            self.progress.emit(
                f"Remove music: {process_elapsed:.1f}s",
                MessageType.PROGRESS,
            )
            self._benchmark_recorder.set_phase_time("processing", process_elapsed)
            self._benchmark_recorder.set_file_size("clean_audio", self.final_audio_path)
            self._benchmark_recorder.set_chunk_info(True, len(chunks))

    def _combine(self) -> None:
        from logic.ffmpeg_utils import combine_video

        self.progress.emit(f"Saving {self.input_video.name}", MessageType.INFO)
        combine_start = time.monotonic()
        try:
            combine_video(self.final_audio_path, self.output_video, self.user_output)
        except (RuntimeError, OSError) as e:
            self.progress.emit("Combination Error: " + str(e), MessageType.ERROR)
            raise

        combine_elapsed = time.monotonic() - combine_start

        if self._benchmark_recorder:
            self.progress.emit(
                f"Combine: {combine_elapsed:.1f}s",
                MessageType.PROGRESS,
            )
            self._benchmark_recorder.set_phase_time("combine", combine_elapsed)

        if self.final_audio_path.exists():
            self.final_audio_path.unlink()
        if self.output_video.exists():
            self.output_video.unlink()

    def _finalize_benchmark(self, success: bool) -> None:
        if not self._benchmark_recorder:
            return
        if not success and not self._benchmark_recorder.has_error():
            self._benchmark_recorder.set_error("Processing failed")
        self._benchmark_recorder.write()
        self._benchmark_recorder.reset()
