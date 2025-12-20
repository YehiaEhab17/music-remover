import os
from pathlib import Path
from enum import Enum

ROOT = Path(__file__).parent.resolve()

YOUTUBE_CLIENTS: list[str] = ["android_sdkless", "web"]

FFMPEG_BINARY_PATH: Path = ROOT / ".binaries" / "ffmpeg" if (os.name == "posix") else ROOT / ".binaries" / "ffmpeg.exe"
DEFAULT_MODEL: str = "UVR-MDX-NET-Voc_FT.onnx"

QUALITY_SETTINGS = {
    "144p": "bestvideo[height<=144]+bestaudio/best",
    "240p": "bestvideo[height<=240]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
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
