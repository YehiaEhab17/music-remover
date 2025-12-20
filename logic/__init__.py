import os
from config import FFMPEG_BINARY_PATH

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

ffmpeg_dir = FFMPEG_BINARY_PATH.parent

# Add to PATH for this Python session
if ffmpeg_dir.exists():
    current_path = os.environ.get("PATH", "")

    if str(ffmpeg_dir) not in current_path:
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}"

else:
    print(f"FFmpeg directory not found at {ffmpeg_dir}")