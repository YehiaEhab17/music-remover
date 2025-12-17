import os
from config import FFMPEG_BINARY_PATH

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

ffmpeg_dir = FFMPEG_BINARY_PATH.parent

# Add to PATH for this Python session
if str(ffmpeg_dir) not in os.environ["PATH"]:
    os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ['PATH']}"

