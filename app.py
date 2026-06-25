import fcntl
import os
import subprocess
import sys
import shutil
import time
from pathlib import Path

if getattr(sys, "frozen", False):
    _nvidia_base = Path(sys._MEIPASS) / "nvidia"
else:
    _nvidia_base = (
        Path(__file__).parent
        / "venv"
        / "lib64"
        / "python3.14"
        / "site-packages"
        / "nvidia"
    )
for _sub in (
    "cudnn/lib",
    "cublas/lib",
    "cuda_runtime/lib",
    "cuda_cupti/lib",
    "cuda_nvrtc/lib",
    "nccl/lib",
    "cu13/lib",
    "cusparselt/lib",
    "nvshmem/lib",
):
    _p = _nvidia_base / _sub
    if _p.exists():
        os.environ["LD_LIBRARY_PATH"] = (
            str(_p) + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        )

if getattr(sys, "frozen", False):
    import importlib.resources as _resources

    _original_open_text = _resources.open_text

    def _patched_open_text(package, resource):
        return (_resources.files(package) / resource).open("r")

    _resources.open_text = _patched_open_text

    import numpy as _np
    from audio_separator.separator.common_separator import CommonSeparator

    _original_write_audio = CommonSeparator.write_audio

    def _patched_write_audio(self, stem_path, stem_source):
        duration_seconds = len(stem_source) / self.sample_rate
        duration_hours = duration_seconds / 3600
        self.logger.info(
            f"Audio duration is {duration_hours:.2f} hours ({duration_seconds:.2f} seconds)."
        )

        if self.use_soundfile:
            self.logger.warning("Using soundfile for writing.")
            self.write_audio_soundfile(stem_path, stem_source)
        else:
            self.logger.info("Using pydub for writing.")
            self.write_audio_pydub(stem_path, stem_source)

    CommonSeparator.write_audio = _patched_write_audio

from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog, QMessageBox

from GUI.main import Ui_MainWindow
from GUI.dialog import Ui_linkDialog
from GUI.settings_dialog import SettingsDialog
from logic.benchmarking import BenchmarkRecorder
from logic.download_utils import DownloadThread
from logic.music_removal import MusicRemoverThread
from logic.utils import get_temp_path, validate_output_directory, create_log, log
from logic import settings_manager

from config import MessageType

TEMP_STALE_MAX_AGE = 24 * 60 * 60  # 24 hours in seconds


def cleanup_stale_temp():
    """Remove temp files/subdirs older than 24 hours on startup."""
    temp = get_temp_path()
    cutoff = time.time() - TEMP_STALE_MAX_AGE
    for entry in temp.iterdir():
        if entry.name == ".lock":
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink(missing_ok=True)
        except OSError:
            pass


def cleanup_video_temp(base_name: str):
    """Remove all temp files for a specific video."""
    subdir = get_temp_path() / base_name
    if subdir.exists():
        shutil.rmtree(subdir, ignore_errors=True)
    for pattern in [f"{base_name}.*", f"{base_name}.*.vtt"]:
        for f in get_temp_path().glob(pattern):
            if f.is_file() and f.name != ".lock":
                f.unlink(missing_ok=True)


COLORS = {
    "INFO": "#2196F3",
    "WARNING": "#FF9800",
    "ERROR": "#F44336",
    "PROGRESS": "#4CAF50",
    "DEBUG": "#9E9E9E",
}


class MyWindow(QMainWindow):
    def __init__(self, log_file) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())
        self.setWindowTitle("Music Remover")

        self.log_file = log_file

        self.download_thread = None
        self.music_remover_thread = None
        self.music_remover_threads = None

        self._processed_count = 0
        self._error_count = 0
        self._total_files = 0

        self.ui.start_button.clicked.connect(self.open_dialog)
        self.ui.output_directory_button.clicked.connect(self.choose_output_directory)
        self.ui.open_output_button.clicked.connect(self._open_output_folder)
        self.ui.settings_button.clicked.connect(self.open_settings)
        self.ui.cancel_button.clicked.connect(self.cancel_processing)
        self.settings = settings_manager.load()
        self.current_source = "From Link"
        self.ui.source_chooser.currentTextChanged.connect(
            lambda source: setattr(self, "current_source", source)
        )

        self.ui.textBrowser.setHtml("")

        default_path = self.settings.get("default_output_path", "")
        self.user_output = Path(default_path) if default_path else Path.cwd()
        self.status_box_text = ""
        self.message_count = 0
        self.ui.output_directory_label.setText(str(self.user_output))

        self.pending_links = []
        self._on_music_complete = None
        self._processed_count = 0
        self._error_count = 0
        self._total_files = 0
        self._summary_shown = True  # cancel swallows summary

        cleanup_stale_temp()

    def _open_output_folder(self) -> None:
        path = str(self.user_output.resolve())
        if os.name == "nt":
            os.startfile(path)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def cancel_processing(self) -> None:
        reply = QMessageBox.question(
            self,
            "Cancel",
            "Stop the current operation?\n\nAny partially processed files will be discarded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.message_handler("Cancelling...", MessageType.WARNING)

        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait(5000)
            self.download_thread = None

        if self.music_remover_thread and self.music_remover_thread.isRunning():
            base_name = self.music_remover_thread.base_name
            self.music_remover_thread.quit()
            self.music_remover_thread.wait(5000)
            self.music_remover_thread = None
            cleanup_video_temp(base_name)
        else:
            self.music_remover_thread = None

        self.music_remover_threads = None
        self.pending_links = []
        self._on_music_complete = None
        self.ui.progress_bar.setValue(0)

        self.set_input_enabled(True)
        self.message_handler("Processing cancelled", MessageType.WARNING)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            settings_manager.save(self.settings)

    def choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose an output path")
        if not directory:
            self.message_handler("please enter a valid directory", MessageType.ERROR)
            return

        is_writable, message = validate_output_directory(Path(directory))
        if not is_writable:
            self.message_handler(message, MessageType.ERROR)
        else:
            self.user_output = Path(directory)
            self.ui.output_directory_label.setText(str(self.user_output))

    def open_dialog(self) -> None:
        self.set_input_enabled(False)
        self.file_input() if (self.current_source == "From File") else self.link_input()

    def file_input(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,  # parent window
            "Select files",  # dialog title
            "",  # starting directory
            "Video Files (*.mp4 *.mov);;All Files (*)",
        )

        files = [Path(f) for f in files]

        if files:
            self._total_files = len(files)
            self._processed_count = 0
            self._error_count = 0
            self._summary_shown = False
            self._processing_source = "file"
            self.remove_music(files)
        else:
            self.message_handler("please select a file", MessageType.ERROR)

    def link_input(self):
        dialog = LinkDialog(
            default_quality=self.settings.get("default_quality", "720p"),
            default_remove_music=self.settings.get("default_remove_music", True),
        )

        if dialog.exec():
            links = dialog.get_links()
            quality = dialog.get_quality()
            is_remove_music = dialog.get_is_remove_music()
            playlist = True if (self.current_source == "From Playlist") else False

            if not links:
                self.message_handler(
                    "Please enter at least one link", MessageType.ERROR
                )
                return

            self.pending_links = list(links)
            self._total_files = len(links)
            self._processed_count = 0
            self._error_count = 0
            self._summary_shown = False
            self._link_quality = quality
            self._link_playlist = playlist
            self._link_remove = is_remove_music
            self._start_next_download()
        else:
            self.message_handler("Please enter a link", MessageType.ERROR)

    def _start_next_download(self):
        if not self.pending_links:
            if not self._summary_shown:
                self._show_summary()
            self.set_input_enabled(True)
            return

        link = self.pending_links.pop(0)
        self.ui.progress_bar.setValue(0)

        remaining = len(self.pending_links) + 1
        if self._total_files > 1:
            self.message_handler(
                f"Downloading ({remaining}/{self._total_files})", MessageType.INFO
            )

        self.download_thread = DownloadThread(
            link,
            self._link_quality,
            self._link_playlist,
            self._link_remove,
            self.user_output,
        )

        self.download_thread.output.connect(self._on_download_done)
        self.download_thread.progress_percent.connect(
            lambda value: self.ui.progress_bar.setValue(int(value))
        )
        self.download_thread.progress.connect(
            lambda msg, msg_type: self.message_handler(msg, msg_type)
        )

        self.download_thread.start()

    def _on_download_done(self, paths):
        if not self._link_remove:
            self._processed_count += 1
        if self._link_remove:
            self._processing_source = "youtube"
            self.remove_music(paths, on_complete=self._start_next_download)
        else:
            self._start_next_download()

    def remove_music(self, paths: list[Path], on_complete=None) -> None:
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait(5000)

        self.ui.progress_bar.setValue(0)
        self._on_music_complete = on_complete
        self.music_remover_threads = iter(paths)
        self._start_next_thread()

    def _start_next_thread(self) -> None:
        try:
            path = next(self.music_remover_threads)

            if self.music_remover_thread and self.music_remover_thread.isRunning():
                self.music_remover_thread.quit()
                self.music_remover_thread.wait(5000)

            benchmark_recorder = BenchmarkRecorder(
                enabled=self.settings.get("benchmarking_enabled", False),
                settings=self.settings,
            )

            self.music_remover_thread = MusicRemoverThread(
                path,
                self.user_output,
                gpu_enabled=self.settings["gpu_enabled"],
                use_tensorrt=self.settings["use_tensorrt"],
                gpu_threads=self.settings["gpu_threads"],
                chunking_enabled=self.settings["chunking_enabled"],
                chunk_secs=self.settings["chunk_duration_secs"],
                cpu_threads=self.settings["cpu_threads"],
                retry_failed_chunks=self.settings["retry_failed_chunks"],
                benchmark_recorder=benchmark_recorder,
                source_type=getattr(self, "_processing_source", "file"),
            )

            self.music_remover_thread.completed.connect(self._on_file_completed)
            self.music_remover_thread.progress_percent.connect(
                lambda value: self.ui.progress_bar.setValue(int(value))
            )
            self.music_remover_thread.progress.connect(
                lambda msg, msg_type: self.message_handler(msg, msg_type)
            )
            self.music_remover_thread.start()

        except StopIteration:
            if self._on_music_complete:
                cb = self._on_music_complete
                self._on_music_complete = None
                cb()
                return

            self._show_summary()
            self.set_input_enabled(True)
            return

    def message_handler(self, message_text: str, message_type: MessageType) -> None:
        message = f"{message_type.value}: {message_text}"
        if not message_type.value == "DEBUG":
            self.message_count += 1
            color = COLORS.get(message_type.value, "#000000")
            self.status_box_text += (
                f'<p style="color:{color};margin:2px 0">'
                f"[{self.message_count}] {message}</p>"
            )
            self.ui.textBrowser.setHtml(self.status_box_text)
        if message_type.value == "ERROR":
            self._error_count += 1
            self.set_input_enabled(True)

        log(self.log_file, message)

    def _on_file_completed(self, success: bool) -> None:
        if self.music_remover_thread:
            cleanup_video_temp(self.music_remover_thread.base_name)
        if success:
            self._processed_count += 1
        self._start_next_thread()

    def _show_summary(self) -> None:
        self._summary_shown = True
        errors = (
            f", {self._error_count} error{'s' if self._error_count != 1 else ''}"
            if self._error_count
            else ""
        )
        self.message_handler(
            f"Done — {self._processed_count} video{'s' if self._processed_count != 1 else ''} processed{errors}",
            MessageType.PROGRESS,
        )

    def set_input_enabled(self, status: bool) -> None:
        self.ui.start_button.setEnabled(status)
        self.ui.start_button.setText("Start" if status else "Processing...")
        self.ui.source_chooser.setEnabled(status)
        self.ui.output_directory_button.setEnabled(status)
        self.ui.cancel_button.setEnabled(not status)


class LinkDialog(QDialog):
    def __init__(
        self, default_quality: str = "720p", default_remove_music: bool = True
    ) -> None:
        super().__init__()
        self.ui = Ui_linkDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.ui.remove_music_box.setChecked(default_remove_music)

        quality_map = {
            "144p": 0,
            "240p": 1,
            "360p": 2,
            "480p": 3,
            "720p": 4,
            "1080p": 5,
        }
        idx = quality_map.get(default_quality, 4)
        self.ui.quality_selector.setCurrentIndex(idx)

    def get_links(self) -> list[str]:
        text = self.ui.links_box.toPlainText()
        return [url.strip() for url in text.split() if url.strip()]

    def get_quality(self) -> str:
        return self.ui.quality_selector.currentText()

    def get_is_remove_music(self) -> bool:
        return self.ui.remove_music_box.isChecked()


def window():
    lock_path = get_temp_path() / ".lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        QMessageBox.critical(
            None, "Already Running", "Music Remover is already running."
        )
        sys.exit(1)

    log_file = create_log()
    log(log_file, "Application started")

    app = QApplication(sys.argv)
    win = MyWindow(log_file)

    win.show()
    try:
        sys.exit(app.exec())
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


window()
