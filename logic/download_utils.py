from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, parse_qs

import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal

import config
from .utils import get_temp_path, get_error_message


def download_video(url: str, quality: str, playlist: bool, output_path: Path, hook: list[Callable]) -> list[Path]:
    format_string = config.QUALITY_SETTINGS.get(quality)

    prefix = "_%(playlist_index)s_ - " if playlist else ""
    output_template = str(output_path / f'{prefix}%(title)s.%(ext)s')

    ydl_opts = {
        'format': format_string,
        'outtmpl': output_template,
        'merge_output_format': config.DEFAULT_OUTPUT_FORMAT,
        'progress_hooks': hook,
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': config.YOUTUBE_CLIENTS,
            }
        }
    }

    query = urlparse(url).query
    if isinstance(query, bytes):
        query = query.decode()
    params = parse_qs(query)

    if not playlist and "list" in params and "v" in params:
        video_index = params.get("index", ["1"])[0]
        ydl_opts["playlist_items"] = video_index

    downloaded_files: list[Path] = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        try:
            info = ydl.extract_info(url, download=True)
        except Exception as e:
            error_message = get_error_message(str(e))
            raise ValueError(error_message)

        downloaded_items = info.get('entries', [info])
        for item in downloaded_items:
            downloaded_files.append(Path(ydl.prepare_filename(item)).resolve())

    return downloaded_files


class DownloadThread(QThread):
    progress: pyqtBoundSignal = pyqtSignal(str)  # for status updates
    progress_percent: pyqtBoundSignal = pyqtSignal(float)  # for the progress bar
    error: pyqtBoundSignal = pyqtSignal(str)  # for errors
    output: pyqtBoundSignal = pyqtSignal(list)  # paths of downloaded files

    def __init__(self, url: str, quality: str, playlist: bool, remove: bool, user_output: Path) -> None:
        super().__init__()
        self.url = url
        self.quality = quality
        self.playlist = playlist
        self.remove = remove  # whether to remove music or just download
        self.user_output = user_output

    def run(self) -> None:
        def hook(d):  # hooks to ytdlp to get status updates, d is a dictionary
            if d['status'] == 'downloading':
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes", 0)

                if total:
                    percent = (downloaded / total) * 100
                else:
                    percent = 0

                self.progress_percent.emit(percent)

        try:
            output_path = get_temp_path() if self.remove else self.user_output

            self.progress.emit(f"Downloading {self.url}")
            file_paths = download_video(self.url, self.quality, self.playlist, output_path, [hook])
            self.progress.emit(f"Finished downloading: {self.url}")

            if self.remove:
                self.output.emit(file_paths)

        except Exception as e:
            self.error.emit("error message while downloading: " + str(e))
