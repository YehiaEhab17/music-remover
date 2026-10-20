import os
import sys
from pathlib import Path

from config import FFMPEG_BINARY_PATH


def setup_nvidia_paths() -> None:
    """Add bundled NVIDIA library directories to LD_LIBRARY_PATH."""
    if getattr(sys, "frozen", False):
        nvidia_base = Path(sys._MEIPASS) / "nvidia"
    else:
        nvidia_base = (
            Path(__file__).parent.parent
            / "venv"
            / "lib64"
            / "python3.14"
            / "site-packages"
            / "nvidia"
        )
    for subdir in (
        "cudnn/lib",
        "cublas/lib",
        "cuda_runtime/lib",
        "cuda_cupti/lib",
        "cuda_nvrtc/lib",
        "nccl/lib",
        "cu13/lib",
        "cusparselt/lib",
        "nvshmem/lib",
    ):
        lib_path = nvidia_base / subdir
        if lib_path.exists():
            os.environ["LD_LIBRARY_PATH"] = (
                str(lib_path) + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            )


def setup_ffmpeg_path() -> None:
    """Add the bundled FFmpeg directory to PATH."""
    ffmpeg_dir = FFMPEG_BINARY_PATH.parent
    if ffmpeg_dir.exists():
        current_path = os.environ.get("PATH", "")
        if str(ffmpeg_dir) not in current_path:
            os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}"
    else:
        print(f"FFmpeg directory not found at {ffmpeg_dir}")


def setup_environment() -> None:
    """Run all environment setup steps. Call once at startup."""
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    setup_nvidia_paths()
    setup_ffmpeg_path()
