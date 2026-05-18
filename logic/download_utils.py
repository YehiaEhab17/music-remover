from typing import Callable
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import subprocess
import re
import shutil
import tempfile
import json

from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal

from config import MessageType
from config import (
    PLAYLIST_TEMPLATE,
    VIDEO_TEMPLATE,
    DEFAULT_OUTPUT_FORMAT,
    YOUTUBE_CLIENTS,
    YOUTUBE_PLAYER_JS_VERSION,
    QUALITY_SETTINGS,
    GIST_CONFIG_URL,
)
from .utils import get_temp_path, get_error_message
from .updater import get_ytdlp_path, fetch_gist_config, check_and_download_ytdlp


def get_playlist_index(url):
    query = urlparse(url).query
    if isinstance(query, bytes):
        query = query.decode()
    params = parse_qs(query)

    if "list" in params:
        video_index = params.get("index", ["1"])[0]
        return video_index


def apply_gist_config(cmd_args: list[str]):
    """Fetches and applies remote config to the yt-dlp command."""
    if not GIST_CONFIG_URL:
        return

    config = fetch_gist_config(GIST_CONFIG_URL)
    if not config:
        return

    # Extract dynamic extractor arguments from Gist
    extractor_args = config.get("extractor_args", {})
    if extractor_args:
        for ex_key, ex_val in extractor_args.items():
            for k, v in ex_val.items():
                if isinstance(v, list):
                    v = ",".join(v)
                cmd_args.extend(["--extractor-args", f"{ex_key}:{k}={v}"])


def download_video(
    url: str,
    quality: str,
    playlist: bool,
    output_path: Path,
    hook_callback: Callable,
    signal: pyqtBoundSignal,
) -> list[Path]:

    # Ensure yt-dlp executable is present
    check_and_download_ytdlp()
    ytdlp_bin = get_ytdlp_path()

    if not ytdlp_bin.exists():
        raise OSError("yt-dlp executable not found. Please check internet connection.")

    format_string = QUALITY_SETTINGS.get(quality, "bestvideo+bestaudio/best")
    video_name = PLAYLIST_TEMPLATE if playlist else VIDEO_TEMPLATE
    output_template = str(output_path / video_name)

    cmd = [
        str(ytdlp_bin),
        "--newline",
        "--ignore-errors",
        "--format",
        format_string,
        "--merge-output-format",
        DEFAULT_OUTPUT_FORMAT,
        "--output",
        output_template,
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "en,ar,fr",
        "--embed-subs",
    ]

    cookies_path = Path("/home/Yehia/Downloads/cookies.txt")
    if cookies_path.exists():
        cmd.extend(["--cookies", str(cookies_path)])

    # Instead of default clients, we load them remotely or use fallback
    if YOUTUBE_CLIENTS and YOUTUBE_PLAYER_JS_VERSION:
        cmd.extend(
            [
                "--extractor-args",
                f"youtube:player_client={','.join(YOUTUBE_CLIENTS)}",
                "--extractor-args",
                f"youtube:player_js_version={','.join(YOUTUBE_PLAYER_JS_VERSION)}",
            ]
        )

    apply_gist_config(cmd)

    if not playlist:
        idx = get_playlist_index(url)
        if idx:
            cmd.extend(["--playlist-items", idx])

    cmd.append(url)

    # Use regex to parse yt-dlp progress
    # e.g., "[download]  15.2% of 50.00MiB at 1.50MiB/s ETA 00:30"
    # or "[download] Destination: somefile.mp4"
    progress_regex = re.compile(r"\[download\]\s+(?P<percent>[0-9.]+)%")
    dest_regex = re.compile(r"\[download\] Destination:\s+(.*)")
    finished_regex = re.compile(r"\[download\]\s+(.*)\s+has already been downloaded")
    merged_regex = re.compile(r'\[Merger\] Merging formats into "(.*)"')

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    downloaded_files = []
    current_file = None

    for line in iter(process.stdout.readline, ""):
        line = line.strip()
        if not line:
            continue

        signal.emit(line, MessageType.DEBUG)

        prog_match = progress_regex.search(line)
        if prog_match:
            percent = float(prog_match.group("percent"))
            hook_callback(
                {"status": "downloading", "percent": percent, "filename": current_file}
            )
            continue

        dest_match = dest_regex.search(line)
        if dest_match:
            current_file = dest_match.group(1)
            downloaded_files.append(Path(current_file).resolve())
            continue

        fin_match = finished_regex.search(line)
        if fin_match:
            current_file = fin_match.group(1)
            downloaded_files.append(Path(current_file).resolve())
            hook_callback({"status": "finished", "filename": current_file})
            continue

        merge_match = merged_regex.search(line)
        if merge_match:
            current_file = merge_match.group(1)
            downloaded_files.append(Path(current_file).resolve())
            hook_callback({"status": "finished", "filename": current_file})
            continue

        if "100%" in line and current_file:
            hook_callback({"status": "finished", "filename": current_file})

    process.wait()

    if process.returncode != 0 and not downloaded_files:
        raise ValueError(f"Download failed with error code {process.returncode}")

    # Remove duplicates from list of files
    downloaded_files = list(set([f for f in downloaded_files if f.exists()]))

    if not downloaded_files:
        raise ValueError("No valid videos found")

    return downloaded_files


class DownloadThread(QThread):
    progress: pyqtBoundSignal = pyqtSignal(str, MessageType)  # for status updates
    progress_percent: pyqtBoundSignal = pyqtSignal(float)  # for the progress bar

    output: pyqtBoundSignal = pyqtSignal(list)  # paths of downloaded files

    def __init__(
        self, url: str, quality: str, playlist: bool, remove: bool, user_output: Path
    ) -> None:
        super().__init__()
        self.url = url
        self.quality = quality
        self.playlist = playlist
        self.remove = remove  # whether to remove music or just download
        self.user_output = user_output

    def run(self) -> None:
        def hook(d):  # hooks to yt-dlp to get status updates, d is a dictionary
            if d["status"] == "downloading":
                percent = d.get("percent", 0.0)
                self.progress_percent.emit(percent)

            elif d["status"] == "finished":
                video_name = Path(d.get("filename", "unknown")).name
                self.progress.emit(
                    f"Finished Downloading: {video_name}", MessageType.PROGRESS
                )

        try:
            output_path = get_temp_path() if self.remove else self.user_output

            self.progress.emit(f"Downloading {self.url}", MessageType.INFO)
            file_paths = download_video(
                self.url,
                self.quality,
                self.playlist,
                output_path,
                hook,
                self.progress,
            )
            self.progress.emit(
                f"Finished downloading: {self.url}", MessageType.PROGRESS
            )

            if self.remove:
                self.output.emit(file_paths)

        except ValueError as e:
            self.progress.emit(str(e), MessageType.ERROR)

        except OSError as e:
            self.progress.emit(f"File system error: {e}", MessageType.ERROR)
