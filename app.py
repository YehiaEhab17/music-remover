import sys
import shutil
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog

from GUI.main import Ui_MainWindow
from GUI.dialog import Ui_linkDialog

from logic.download_utils import DownloadThread
from logic.music_removal import MusicRemoverThread
from logic.utils import get_temp_path, validate_output_directory

from config import MessageType

# TODO: ADD HELP
# TODO : ADD TRANSLATION
# TODO: add gpu accel


class MyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.download_thread = None
        self.music_remover_thread = None
        self.music_remover_threads = None

        self.ui.start_button.clicked.connect(self.open_dialog)
        self.ui.output_directory_button.clicked.connect(self.choose_output_directory)
        self.current_source = "From Link"
        self.ui.source_chooser.currentTextChanged.connect(lambda source: setattr(self, "current_source", source))

        self.user_output = Path.cwd()
        self.status_box_text = ""
        self.message_count = 0
        self.ui.output_directory_label.setText(str(self.user_output))

        try:
            shutil.rmtree(get_temp_path())
        except OSError:
            self.message_handler("Failed to remove temp directory", MessageType.ERROR)

    def choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose an output path")
        if not directory:
            self.message_handler("please enter a valid directory", MessageType.ERROR)

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
            "Video Files (*.mp4 *.mov);;All Files (*)"
        )

        files = [Path(f) for f in files]

        if files:
            self.remove_music(files)
        else:
            self.message_handler("please select a file", MessageType.ERROR)

    def link_input(self):
        dialog = LinkDialog()

        if dialog.exec():
            link = dialog.get_link()
            quality = dialog.get_quality()
            is_remove_music = dialog.get_is_remove_music()
            playlist = True if (self.current_source == "From Playlist") else False

            # Start the download in a separate thread
            self.download_thread = DownloadThread(link, quality, playlist, is_remove_music, self.user_output)

            self.download_thread.output.connect(lambda paths: self.remove_music(paths))
            self.download_thread.progress_percent.connect(lambda value: self.ui.progress_bar.setValue(int(value)))
            self.download_thread.progress.connect(lambda msg, msg_type: self.message_handler(msg, msg_type))

            self.download_thread.start()
        else:
            self.message_handler("Please enter a link", MessageType.ERROR)

    def remove_music(self, paths: list[Path]) -> None:
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait(5000)

        self.music_remover_threads = iter(paths)
        self.start_next_thread()

    def start_next_thread(self) -> None:
        try:
            path = next(self.music_remover_threads)

            if self.music_remover_thread and self.music_remover_thread.isRunning():
                self.music_remover_thread.quit()
                self.music_remover_thread.wait(5000)

            self.music_remover_thread = MusicRemoverThread(path, self.user_output)

            self.music_remover_thread.completed.connect(self.start_next_thread)
            self.music_remover_thread.progress_percent.connect(lambda value: self.ui.progress_bar.setValue(int(value)))
            self.music_remover_thread.progress.connect(lambda msg, msg_type: self.message_handler(msg, msg_type))
            self.music_remover_thread.start()


        except StopIteration:
            self.message_handler("All files processed", MessageType.PROGRESS)
            try:
                shutil.rmtree(get_temp_path())
            except OSError:
                self.message_handler("Failed to remove temp directory", MessageType.ERROR)
            self.set_input_enabled(True)
            return

    def message_handler(self, message_text: str, message_type: MessageType) -> None:
        if not message_type.value == "DEBUG":
            self.message_count += 1
            self.status_box_text += f"[{self.message_count}]: {message_type.value}: {message_text} \n\n"
            if message_type.value == "ERROR":
                self.set_input_enabled(True)

            self.ui.textBrowser.setText(self.status_box_text)
        else:
            print(message_type.value, message_text)

    def set_input_enabled(self, status: bool) -> None:
        self.ui.start_button.setEnabled(status)
        self.ui.source_chooser.setEnabled(status)
        self.ui.output_directory_button.setEnabled(status)


class LinkDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_linkDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

    def get_link(self) -> str:
        return self.ui.link_box.text()

    def get_quality(self) -> str:
        return self.ui.quality_selector.currentText()

    def get_is_remove_music(self) -> bool:
        return self.ui.remove_music_box.isChecked()


def window():
    app = QApplication(sys.argv)
    win = MyWindow()

    win.show()
    sys.exit(app.exec())


window()
