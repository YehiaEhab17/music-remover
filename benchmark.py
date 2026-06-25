#!/usr/bin/env python3
"""Benchmark script for music-remover.

Tests different configurations and reports timings + VRAM usage.

Usage:
    python benchmark.py <video_path>
"""

import sys
import time
import subprocess
import threading
from pathlib import Path

from logic import setup_environment

setup_environment()

import torch
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from logic.music_removal import MusicRemoverThread
from logic.utils import get_temp_path


# ── VRAM Monitor ──────────────────────────────────────────────────────────────


class VRAMMonitor:
    """Background thread that polls nvidia-smi for peak VRAM usage."""

    def __init__(self):
        self._peak_mb = 0.0
        self._running = False
        self._thread = None

    def start(self):
        self._peak_mb = 0.0
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self) -> float:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        return self._peak_mb

    def _poll(self):
        while self._running:
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    vram_mb = float(result.stdout.strip().split("\n")[0])
                    self._peak_mb = max(self._peak_mb, vram_mb)
            except (subprocess.TimeoutExpired, ValueError, IndexError):
                pass
            time.sleep(0.5)


# ── Test Runner ───────────────────────────────────────────────────────────────

CONFIGS = [
    {
        "name": "GPU 1T",
        "gpu_enabled": True,
        "use_tensorrt": False,
        "gpu_threads": 1,
        "cpu_threads": 1,
    },
    {
        "name": "GPU 1T + TensorRT",
        "gpu_enabled": True,
        "use_tensorrt": True,
        "gpu_threads": 1,
        "cpu_threads": 1,
    },
    {
        "name": "GPU 2T",
        "gpu_enabled": True,
        "use_tensorrt": False,
        "gpu_threads": 2,
        "cpu_threads": 1,
    },
    {
        "name": "CPU 1T",
        "gpu_enabled": False,
        "use_tensorrt": False,
        "gpu_threads": 1,
        "cpu_threads": 1,
    },
    {
        "name": "CPU 2T",
        "gpu_enabled": False,
        "use_tensorrt": False,
        "gpu_threads": 1,
        "cpu_threads": 2,
    },
    {
        "name": "CPU 4T",
        "gpu_enabled": False,
        "use_tensorrt": False,
        "gpu_threads": 1,
        "cpu_threads": 4,
    },
]


class BenchmarkRunner(QThread):
    """Runs a single benchmark config on a background thread."""

    def __init__(self, video_path: Path, config: dict):
        super().__init__()
        self.video_path = video_path
        self.config = config
        self.result = None
        self.error = None

    def run(self):
        try:
            from logic.ffmpeg_utils import (
                split_video,
                combine_video,
                get_audio_duration,
            )

            temp_dir = get_temp_path()
            temp_dir.mkdir(parents=True, exist_ok=True)
            base_name = self.video_path.stem
            output_audio = temp_dir / f"{base_name}_AUDIO.wav"
            output_video = temp_dir / f"{base_name}_VIDEO.mp4"
            output_dir = Path.home() / "Videos" / "MusicRemover"
            output_dir.mkdir(parents=True, exist_ok=True)

            timings = {}
            vram_monitor = VRAMMonitor()

            # Split
            t0 = time.monotonic()
            split_video(self.video_path, output_audio, output_video)
            timings["split"] = time.monotonic() - t0

            audio_duration = get_audio_duration(output_audio)
            audio_size_mb = output_audio.stat().st_size / (1024 * 1024)

            # Process
            vram_monitor.start()
            t0 = time.monotonic()

            thread = MusicRemoverThread(
                input_video=self.video_path,
                user_output=output_dir,
                gpu_enabled=self.config["gpu_enabled"],
                use_tensorrt=self.config["use_tensorrt"],
                gpu_threads=self.config["gpu_threads"],
                cpu_threads=self.config["cpu_threads"],
                chunking_enabled=True,
                chunk_secs=60,
                retry_failed_chunks=True,
                source_type="benchmark",
            )
            # Override paths for benchmark
            thread.temp_dir = temp_dir
            thread.output_audio = output_audio
            thread.output_video = output_video

            if audio_size_mb > 50:
                thread._process_chunked()
            else:
                thread._process_normal()

            timings["process"] = time.monotonic() - t0
            peak_vram = vram_monitor.stop()

            # Combine
            final_audio = thread.final_audio_path
            final_video = output_dir / output_video.name
            t0 = time.monotonic()
            combine_video(final_audio, output_video, output_dir)
            timings["combine"] = time.monotonic() - t0

            timings["total"] = (
                timings["split"] + timings["process"] + timings["combine"]
            )

            self.result = {
                "timings": timings,
                "peak_vram_mb": peak_vram,
                "audio_duration": audio_duration,
                "audio_size_mb": audio_size_mb,
                "chunked": audio_size_mb > 50,
            }

            # Cleanup
            for f in temp_dir.glob(f"{base_name}*"):
                f.unlink(missing_ok=True)
            if final_video.exists():
                final_video.unlink()

        except Exception as e:
            self.error = str(e)
            import traceback

            self.error_traceback = traceback.format_exc()


def run_benchmark(video_path: Path):
    """Run all benchmark configs and print results."""

    print("=" * 70)
    print("MUSIC REMOVER BENCHMARK")
    print("=" * 70)
    print(f"Video: {video_path.name}")
    print(f"Size: {video_path.stat().st_size / (1024 * 1024):.1f} MB")
    print(
        f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}"
    )
    print(
        f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
        if torch.cuda.is_available()
        else ""
    )
    print("=" * 70)
    print()

    results = []

    for i, config in enumerate(CONFIGS):
        name = config["name"]
        print(f"[{i + 1}/{len(CONFIGS)}] Testing: {name}")
        print(
            f"  GPU={config['gpu_enabled']}, TensorRT={config['use_tensorrt']}, "
            f"GPU Threads={config['gpu_threads']}, CPU Threads={config['cpu_threads']}"
        )

        runner = BenchmarkRunner(video_path, config)
        runner.start()

        # Wait for completion, printing progress dots
        dot_count = 0
        while runner.isRunning():
            QApplication.processEvents()
            time.sleep(0.5)
            dot_count += 1
            if dot_count % 2 == 0:
                print(".", end="", flush=True)
        print()

        if runner.error:
            print(f"  ERROR: {runner.error}")
            results.append({"name": name, "error": runner.error})
        else:
            r = runner.result
            timings = r["timings"]
            print(f"  Split:    {timings['split']:.1f}s")
            print(f"  Process:  {timings['process']:.1f}s")
            print(f"  Combine:  {timings['combine']:.1f}s")
            print(f"  Total:    {timings['total']:.1f}s")
            print(f"  Peak VRAM: {r['peak_vram_mb']:.0f} MB")
            print(f"  Chunks: {'yes' if r['chunked'] else 'no'}")
            results.append({"name": name, **r})

        print()

        # Cleanup between runs
        gc_cleanup()

    # ── Results Table ─────────────────────────────────────────────────────────

    print("=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)
    print()

    # Header
    print(
        f"{'Config':<20} {'Split':>8} {'Process':>10} {'Combine':>10} {'Total':>8} {'VRAM':>8} {'Status':>8}"
    )
    print("-" * 70)

    best_total = float("inf")
    best_name = ""

    for r in results:
        name = r["name"]
        if "error" in r and "timings" not in r:
            print(
                f"{name:<20} {'—':>8} {'—':>10} {'—':>10} {'—':>8} {'—':>8} {'FAIL':>8}"
            )
        else:
            t = r["timings"]
            total = t["total"]
            vram = r.get("peak_vram_mb", 0)
            status = "OK"
            if total < best_total:
                best_total = total
                best_name = name
            print(
                f"{name:<20} {t['split']:>7.1f}s {t['process']:>9.1f}s {t['combine']:>9.1f}s {total:>7.1f}s {vram:>6.0f}MB {status:>8}"
            )

    print("-" * 70)
    print()
    if best_name:
        print(f"FASTEST: {best_name} ({best_total:.1f}s)")
    print()


def gc_cleanup():
    """Clean up GPU memory between runs."""
    import gc

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    time.sleep(1)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark.py <video_path>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    app = QApplication(sys.argv)
    run_benchmark(video_path)
