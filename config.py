import os
from pathlib import Path

# FFmpeg Configuration
FFMPEG_BINARY_PATH: Path = Path(".binaries/ffmpeg") if (os.name == "posix") else Path(".binaries/ffmpeg.exe")

# Video Quality Settings
QUALITY_SETTINGS = {
    "144p": "bestvideo[height<=144]+bestaudio/best",
    "240p": "bestvideo[height<=240]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
}

# Audio Processing Settings
AUDIO_SETTINGS = {
    "sample_rate": "44100",
    "channels": "2",
    "codec": "pcm_s16le",
    "output_bitrate": "192k",
    "highpass_freq": "100",
    "lowpass_freq": "9000",
}
# Model Settings
DEFAULT_MODEL: str = "UVR-MDX-NET-Voc_FT.onnx"
# Output Settings
DEFAULT_OUTPUT_FORMAT: str = "mp4"
# YouTube Client Settings
YOUTUBE_CLIENTS: list[str] = ["android_sdkless", "web"]

ERROR_MESSAGES = {
    # yt-dlp specific errors
    "invalid url": "Invalid URL: Please check the URL format and try again.",
    "private video": "Private video: This video is private and cannot be accessed.",
    "sign in to confirm your age": "Age-restricted: This video requires age verification.",
    "video unavailable": "Video unavailable: This video has been removed or is not accessible.",
    "members only": "Members-only content: This video requires channel membership.",
    "geo restriction": "Geo-restricted: This video is not available in your country.",

    # File system errors
    "permission denied": "Permission denied: Check file/directory permissions.",
    "no such file": "File not found: The specified file does not exist.",
    "no such directory": "Directory not found: The specified directory does not exist.",

    # Network errors
    "unable to download": "Download failed: Unable to download from this URL.",
    "network error": "Network error: Check your internet connection.",

    # Processing errors
    "ffmpeg failed": "Processing error: Video processing failed.",
    "model failed": "AI model error: Music removal processing failed.",
}
# Generic fallback error
GENERIC_ERROR_MESSAGE = "An error occurred: {error_details}"