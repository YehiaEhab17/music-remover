import os
from pathlib import Path
from enum import Enum

ROOT = Path(__file__).parent.resolve()

# YOUTUBE_CLIENTS: list[str] = ["android_sdkless", "web"]
YOUTUBE_CLIENTS: list[str] = ["default", "-web_safari"]
YOUTUBE_PLAYER_JS_VERSION: list[str] = ["actual"]
GIST_CONFIG_URL: str = (
    "https://raw.githubusercontent.com/YehiaEhab17/music-remover/main/ytdlp-config.json"
)


FFMPEG_BINARY_PATH: Path = (
    ROOT / ".binaries" / "ffmpeg"
    if (os.name == "posix")
    else ROOT / ".binaries" / "ffmpeg.exe"
)
DEFAULT_MODEL: str = "UVR-MDX-NET-Voc_FT.onnx"

QUALITY_SETTINGS = {
    "144p": "bv*[height<=144]+ba/b",
    "240p": "bv*[height<=240]+ba/b",
    "360p": "bv*[height<=360]+ba/b",
    "480p": "bv*[height<=480]+ba/b",
    "720p": "bv*[height<=720]+ba/b",
    "1080p": "bv*[height<=1080]+ba/b",
}


AUDIO_SETTINGS = {
    "sample_rate": "44100",
    "channels": "2",
    "codec": "pcm_s16le",
    "output_bitrate": "192k",
    "highpass_freq": "100",
    "lowpass_freq": "9000",
}

DEFAULT_OUTPUT_FORMAT: str = "mp4"

VIDEO_TEMPLATE = "%(title)s.%(ext)s"

PLAYLIST_TEMPLATE = "_%(playlist_index)s_-%(title)s.%(ext)s"

ERROR_MESSAGES = {
    "invalid url": "Invalid URL: Please check the URL format and try again.",
    "private video": "Private video: This video is private and cannot be accessed.",
    "sign in to confirm your age": "Age-restricted: This video requires age verification.",
    "video unavailable": "Video unavailable: This video has been removed or is not accessible.",
    "members only": "Members-only content: This video requires channel membership.",
    "geo restriction": "Geo-restricted: This video is not available in your country.",
    "ffmpeg": "Please enter a valid video file",
    "ffmpeg failed": "Processing error: Video processing failed.",
    "model failed": "AI model error: Music removal processing failed.",
}

GENERIC_ERROR_MESSAGE = "An error occurred: {error_details}"


class MessageType(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    PROGRESS = "PROGRESS"
