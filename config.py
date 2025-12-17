from pathlib import Path
import os

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
    "sample_rate": 44100,
    "channels": 2,
    "codec": "pcm_s16le",
    "output_bitrate": "192k",
    "highpass_freq": 100,
    "lowpass_freq": 9000,
}
# Model Settings
DEFAULT_MODEL: str = "UVR-MDX-NET-Voc_FT.onnx"
# Output Settings
DEFAULT_OUTPUT_FORMAT: str = "mp4"
# YouTube Client Settings
YOUTUBE_CLIENTS: list[str] = ["android_sdkless", "web"]