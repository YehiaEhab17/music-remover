import subprocess
from pathlib import Path

import config


def split_video(input_video: Path, output_audio: Path, output_video: Path) -> None:

    audio_command = [
        "ffmpeg",
        "-y",
        "-i", str(input_video),
        "-vn",
        "-ar", config.AUDIO_SETTINGS["sample_rate"],
        "-ac", config.AUDIO_SETTINGS["channels"],
        "-acodec", config.AUDIO_SETTINGS["codec"],
        str(output_audio),
    ]

    video_command = [
        "ffmpeg",
        "-y",
        "-i", str(input_video),
        "-an",
        "-vcodec", "copy",
        str(output_video),
    ]

    try:
        subprocess.run(audio_command, check=True, capture_output=True, text=True)
        subprocess.run(video_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("FFmpeg failed:", e.stderr)
        raise


def combine_video(input_audio: Path, input_video: Path, output_dir: Path) -> Path:
    output_video: Path = output_dir / input_video.name

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_video),
        "-i", str(input_audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", config.AUDIO_SETTINGS["output_bitrate"],
        "-af", f"highpass=f={config.AUDIO_SETTINGS['highpass_freq']}, lowpass=f={config.AUDIO_SETTINGS['lowpass_freq']}",
        str(output_video),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("FFmpeg failed:", e.stderr)
        raise
