import subprocess
from pathlib import Path


def split_video(input_video: Path, output_audio: Path, output_video: Path) -> None:

    audio_command = [
        "ffmpeg"
        "-y",
        "-i", str(input_video),
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-acodec", "pcm_s16le",
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
        "-b:a", "192k",
        "-af", "highpass=f=100, lowpass=f=9000",
        str(output_video),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("FFmpeg failed:", e.stderr)
        raise
