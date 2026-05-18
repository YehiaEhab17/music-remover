import re
import sys
import threading
from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal
from audio_separator.separator import Separator
from pathlib import Path
import torch

from config import MessageType, DEFAULT_MODEL
from .utils import get_temp_path, get_resource_path


class StreamCatcher:
    """Intercepts terminal output to capture tqdm progress for the GUI."""

    def __init__(self, signal, original_stderr):
        self.signal = signal
        self.original_stderr = original_stderr
        self.regex = re.compile(r"(\d{1,3})%")

    def write(self, text):
        self.original_stderr.write(text)  # Still print to terminal
        match = self.regex.search(text)
        if match:
            percent = float(match.group(1))
            self.signal.emit(percent)

    def flush(self):
        self.original_stderr.flush()


class MusicRemoverThread(QThread):
    progress: pyqtBoundSignal = pyqtSignal(str, MessageType)  # for status updates
    progress_percent: pyqtBoundSignal = pyqtSignal(float)
    completed: pyqtBoundSignal = pyqtSignal(bool)

    def __init__(self, input_video: Path, user_output: Path) -> None:
        super().__init__()
        self.input_video: Path = input_video
        self.user_output: Path = user_output
        self.temp_dir: Path = get_temp_path()

        self.base_name: str = self.input_video.stem

        self.output_audio: Path = self.temp_dir / f"{self.base_name}_AUDIO.wav"
        self.output_video: Path = self.temp_dir / f"{self.base_name}_VIDEO.mp4"

        self.final_audio_path: Path = Path()

    def run(self) -> None:
        from logic.ffmpeg_utils import split_video

        try:
            self.temp_dir = get_temp_path()

            self.progress.emit(f"Splitting {self.input_video}", MessageType.DEBUG)
            split_video(self.input_video, self.output_audio, self.output_video)
            self.progress.emit(
                f"Finished Splitting {self.input_video}", MessageType.DEBUG
            )

        except (RuntimeError, OSError) as e:
            self.progress.emit("Splitting Error: " + str(e), MessageType.ERROR)
            self.completed.emit(False)
            return

        try:
            is_cuda_available = torch.cuda.is_available()
            if is_cuda_available:
                self.progress.emit(
                    f"GPU acceleration enabled: {torch.cuda.get_device_name(0)}",
                    MessageType.DEBUG,
                )

            separator: Separator = Separator(
                output_dir=str(self.temp_dir),
                model_file_dir=get_resource_path(".models"),
                use_autocast=is_cuda_available,
            )
            separator.load_model(DEFAULT_MODEL)

            self.progress.emit(
                f"Removing music from {self.input_video.name}", MessageType.INFO
            )

            # --- Inject the progress bar stream catcher ---
            original_stderr = sys.stderr
            catcher = StreamCatcher(self.progress_percent, original_stderr)
            sys.stderr = catcher

            try:
                output_files: list[str] = separator.separate(str(self.output_audio))
            finally:
                # Always restore the original stderr so we don't break the app
                sys.stderr = original_stderr
            # -----------------------------------------------

            if self.output_audio.exists():
                self.output_audio.unlink()

            self.progress.emit(
                f"Finished Removing music from {self.input_video.name}",
                MessageType.PROGRESS,
            )

            self.final_audio_path: Path = self.temp_dir / Path(output_files[1])

        except Exception as e:
            self.progress.emit("Music Removal Error: " + str(e), MessageType.ERROR)
            self.completed.emit(False)
            raise

        try:
            from logic.ffmpeg_utils import combine_video

            self.progress.emit(f"Saving {self.input_video.name}", MessageType.INFO)
            combine_video(self.final_audio_path, self.output_video, self.user_output)
            self.progress.emit(
                f"Finished Saving {self.input_video.name}", MessageType.DEBUG
            )

            self.completed.emit(True)

            try:
                if self.final_audio_path.exists():
                    self.final_audio_path.unlink()
                if self.output_video.exists():
                    self.output_video.unlink()
            except OSError:
                pass

        except (RuntimeError, OSError) as e:
            self.progress.emit("Combination Error: " + str(e), MessageType.ERROR)
            self.completed.emit(False)
