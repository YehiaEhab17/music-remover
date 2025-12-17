

import yt_dlp
from .ffmpeg_utils import load_ffmpeg
from urllib.parse import urlparse, parse_qs
from PyQt6.QtCore import QThread, pyqtSignal
from .temp_utils import get_temp_path
from pathlib import Path

def download_video(url, quality, playlist, output_path : Path, hook):
    QUALITY_MAP = {
        "144p": "bestvideo[height<=144]+bestaudio/best",
        "240p": "bestvideo[height<=240]+bestaudio/best",
        "360p": "bestvideo[height<=360]+bestaudio/best",
        "480p": "bestvideo[height<=480]+bestaudio/best",
        "720p": "bestvideo[height<=720]+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best",
    }

    ffmpeg_path = load_ffmpeg()

    format_string = QUALITY_MAP.get(quality)

    prefix = "_%(playlist_index)s_ - " if playlist else ""
    output_template = str(output_path / f'{prefix}%(title)s.%(ext)s')

    ydl_opts = {
        'format': format_string,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',  # ensures audio+video merges as mp4
        'ffmpeg_location' : str(ffmpeg_path),
        'progress_hooks': hook,
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_sdkless', 'web'],
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

    downloaded_files = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)  # extract info AND download

        # Determine the list of downloaded items (either the single info dict, or the list of entries)
        # We wrap the single item in a list for uniform processing.
        downloaded_items = info.get('entries', [info])

        # Iterate over the list of items to get the absolute path for each downloaded file
        for item in downloaded_items:
            downloaded_files.append(Path(ydl.prepare_filename(item)).resolve())

    return downloaded_files


class DownloadThread(QThread):
    progress = pyqtSignal(str)  # for status updates
    progress_percent = pyqtSignal(float) # for the progress bar
    error = pyqtSignal(str) # for errors
    output = pyqtSignal(list) # paths of downloaded files

    def __init__(self, link, quality, playlist, remove, user_output):
        super().__init__()
        self.link = link        # store the video link
        self.quality = quality  # store the selected quality
        self.playlist = playlist # store whether we are downloading a playlist or not
        self.remove = remove # whether to remove music or just download
        self.user_output = user_output

    def run(self):
        def hook(d): # hooks to ytdlp to get status updates, d is a dictionary
            if d['status'] == 'downloading':

                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes", 0)

                if total:
                    percent = (downloaded / total) * 100
                else:
                    percent = 0

                self.progress_percent.emit(percent)

        # this method executes when the thread starts
        try:
            output_path = get_temp_path() if self.remove else self.user_output
            self.progress.emit(f"Downloading {self.link}")
            file_paths = download_video(self.link, self.quality, self.playlist, output_path, [hook])    # call your existing download function
            self.progress.emit(f"Finished downloading: {self.link}")  # send a message back to GUI
            if self.remove:
                self.output.emit(file_paths)


        except Exception as e:
            self.error.emit("error message while downloading: " + str(e))




