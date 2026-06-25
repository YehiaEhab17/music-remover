import shutil
import subprocess
from pathlib import Path

import soundfile as sf

import config
from .utils import get_error_message


def split_video(input_video: Path, output_audio: Path, output_video: Path) -> None:

    audio_command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(input_video),
        "-vn",
        "-ar",
        config.AUDIO_SETTINGS["sample_rate"],
        "-ac",
        config.AUDIO_SETTINGS["channels"],
        "-acodec",
        config.AUDIO_SETTINGS["codec"],
        str(output_audio),
    ]

    video_command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(input_video),
        "-an",
        "-vcodec",
        "copy",
        "-scodec",
        "copy",  # Copy subtitle stream
        str(output_video),
    ]

    try:
        subprocess.run(audio_command, check=True, capture_output=True, text=True)
        subprocess.run(video_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        error_message = get_error_message(e.stderr)
        raise RuntimeError(error_message) from e


def combine_video(input_audio: Path, input_video: Path, output_dir: Path) -> None:
    output_video: Path = output_dir / input_video.name

    command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(input_video),  # Input 0
        "-i",
        str(input_audio),  # Input 1
        "-map",
        "0:v",  # Take video from the original video file
        "-map",
        "1:a",  # Take the new, clean audio
        "-map",
        "0:s?",  # Take subtitles from the video file (the '?' prevents errors if missing)
        "-c:v",
        "copy",  # Keep video quality exactly as is
        "-c:a",
        "aac",  # Encode the new audio to AAC
        "-c:s",
        "mov_text",  # Encode subtitles so they work in MP4 players
        "-b:a",
        config.AUDIO_SETTINGS["output_bitrate"],
        "-af",
        f"highpass=f={config.AUDIO_SETTINGS['highpass_freq']}, lowpass=f={config.AUDIO_SETTINGS['lowpass_freq']}",
        str(output_video),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        error_message = get_error_message(e.stderr)
        raise RuntimeError(error_message) from e


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def split_audio_chunks(
    audio_path: Path, chunk_secs: int, context_secs: int
) -> list[Path]:
    temp_dir = audio_path.parent
    base = audio_path.stem
    total_dur = get_audio_duration(audio_path)
    step = chunk_secs
    chunk_paths = []
    idx = 0
    start = 0.0

    while start < total_dur:
        seg_start = max(0.0, start - context_secs)
        seg_end = min(total_dur, start + chunk_secs + context_secs)
        seg_dur = seg_end - seg_start

        output = temp_dir / f"{base}_chunk_{idx:04d}.wav"
        result = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                str(seg_start),
                "-t",
                str(seg_dur),
                "-i",
                str(audio_path),
                "-acodec",
                "pcm_s16le",
                "-ar",
                config.AUDIO_SETTINGS["sample_rate"],
                "-ac",
                config.AUDIO_SETTINGS["channels"],
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg chunk {idx} failed (rc={result.returncode}): {result.stderr}"
            )
        if not output.exists():
            raise RuntimeError(
                f"ffmpeg chunk {idx} succeeded but output file missing: {output}"
            )
        chunk_paths.append(output)
        start += step
        idx += 1

    return chunk_paths


def combine_audio_chunks(
    chunk_paths: list[Path],
    context_secs: int,
    output_path: Path,
    sample_rate: int = int(config.AUDIO_SETTINGS["sample_rate"]),
) -> None:
    n = len(chunk_paths)
    if n == 0:
        raise ValueError("No chunks to combine")
    if n == 1:
        shutil.move(str(chunk_paths[0]), str(output_path))
        return

    context_samples = int(context_secs * sample_rate)

    with sf.SoundFile(
        str(output_path),
        mode="w",
        samplerate=sample_rate,
        channels=2,
        subtype="PCM_16",
    ) as out:
        for i, path in enumerate(chunk_paths):
            data, sr = sf.read(str(path), dtype="float32")
            if sr != sample_rate:
                raise RuntimeError(
                    f"Sample rate mismatch: expected {sample_rate}, got {sr}"
                )

            lo = context_samples if i > 0 else 0
            hi = -context_samples if i < n - 1 else None
            trimmed = data[lo:hi] if hi is not None else data[lo:]

            out.write(trimmed)
