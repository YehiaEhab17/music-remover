from typing import Callable
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal

from config import MessageType
from config import PLAYLIST_TEMPLATE, VIDEO_TEMPLATE, DEFAULT_OUTPUT_FORMAT, YOUTUBE_CLIENTS, QUALITY_SETTINGS
from .utils import get_temp_path, get_error_message


class LoggerOutputs:
    def __init__(self, signal):
        self.signal = signal

    def error(self, msg):
        self.signal.emit(get_error_message(msg), MessageType.WARNING)

    def warning(self, msg):
        self.signal.emit(get_error_message(msg), MessageType.DEBUG)

    def debug(self, msg):
        self.signal.emit(msg, MessageType.DEBUG)


def get_playlist_index(url):
    query = urlparse(url).query
    if isinstance(query, bytes):
        query = query.decode()
    params = parse_qs(query)

    if "list" in params:
        video_index = params.get("index", ["1"])[0]
        return video_index



def download_video(
        url: str,
        quality: str,
        playlist: bool,
        output_path: Path,
        hook: list[Callable],
        signal: pyqtBoundSignal
) -> list[Path]:

    format_string = QUALITY_SETTINGS.get(quality)
    video_name = PLAYLIST_TEMPLATE if playlist else VIDEO_TEMPLATE
    output_template = str(output_path / video_name)

    ydl_opts = {
        'format': format_string,
        'outtmpl': output_template,
        'merge_output_format': DEFAULT_OUTPUT_FORMAT,
        'progress_hooks': hook,
        'quiet': True,
        'ignoreerrors': True,
        "logger": LoggerOutputs(signal),
        'extractor_args': {'youtube': {'player_client': YOUTUBE_CLIENTS, }}}
    if not playlist:
        ydl_opts["playlist_items"] = get_playlist_index(url)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        entries = info.get('entries', [info]) if info else []

        downloaded_files = [
            Path(ydl.prepare_filename(entry)).resolve()
            for entry in entries
            if entry
        ]

    if not downloaded_files:
        raise ValueError("No valid videos found")

    return downloaded_files


class DownloadThread(QThread):
    progress: pyqtBoundSignal = pyqtSignal(str, MessageType)  # for status updates
    progress_percent: pyqtBoundSignal = pyqtSignal(float)  # for the progress bar

    output: pyqtBoundSignal = pyqtSignal(list)  # paths of downloaded files

    def __init__(self, url: str, quality: str, playlist: bool, remove: bool, user_output: Path) -> None:
        super().__init__()
        self.url = url
        self.quality = quality
        self.playlist = playlist
        self.remove = remove  # whether to remove music or just download
        self.user_output = user_output

    def run(self) -> None:
        def hook(d):  # hooks to yt-dlp to get status updates, d is a dictionary
            if d['status'] == 'downloading':
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes", 0)

                percent = ((downloaded / total) * 100) if total else 0
                # TODO : add eta
                self.progress_percent.emit(percent)

            elif d['status'] == 'finished':
                video_name = Path(d.get('filename')).name
                self.progress.emit(f"Finished Downloading: {video_name}", MessageType.PROGRESS)

        try:
            output_path = get_temp_path() if self.remove else self.user_output

            self.progress.emit(f"Downloading {self.url}", MessageType.INFO)
            file_paths = download_video(self.url, self.quality, self.playlist, output_path, [hook], self.progress)
            self.progress.emit(f"Finished downloading: {self.url}", MessageType.PROGRESS)

            if self.remove:
                self.output.emit(file_paths)

        except ValueError as e:
            self.progress.emit(str(e), MessageType.ERROR)

        except OSError as e:
            self.progress.emit(f"File system error: {e}", MessageType.ERROR)
