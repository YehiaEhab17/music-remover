from pathlib import Path
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog
from GUI.main import Ui_MainWindow
from GUI.dialog import Ui_linkDialog
from logic.download import DownloadThread
from logic.demucs_utils import MusicRemoverThread
from logic.temp_utils import get_temp_path
import shutil

#TODO: ADD HELP
#TODO : ADD TRANSLATION
#TODO: add gpu accel

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.ui.start_button.clicked.connect(self.open_dialog)
        self.ui.output_directory_button.clicked.connect(self.choose_output_directory)
        self.current_source = "From Link"
        self.ui.source_chooser.currentTextChanged.connect(lambda source:
                                                          setattr(self, "current_source", source))

        self.user_output= Path.cwd()
        self.ui.output_directory_label.setText(str(self.user_output))

    def remove_music(self, paths):
        self.music_remover_threads = iter(paths)
        self.start_next_thread()

    def choose_output_directory(self):
        self.user_output = Path(QFileDialog.getExistingDirectory(self, "Choose an output path"))
        self.ui.output_directory_label.setText(str(self.user_output))


    def open_dialog(self):
        self.ui.start_button.setEnabled(False)
        self.ui.source_chooser.setEnabled(False)
        self.ui.output_directory_button.setEnabled(False)

        try:
            if self.current_source == "From File":
                files, _ = QFileDialog.getOpenFileNames(
                    self,                     # parent window
                    "Select files",           # dialog title
                    "",                       # starting directory
                    "Video Files (*.mp4 *.mov, );;All Files (*)"
                )
                files = [Path(f) for f in files]

                if files:
                    self.remove_music(files)

            else:
                self.playlist = (True) if (self.current_source == "From Playlist") else (False)
                dialog = LinkDialog()

                if dialog.exec():
                    link = dialog.get_link()
                    quality = dialog.get_quality()
                    is_remove_music = dialog.get_is_remove_music()

                    # Start the download in a separate thread
                    self.download_thread = DownloadThread(link, quality, self.playlist, is_remove_music, self.user_output)
                    self.download_thread.output.connect(lambda paths: self.remove_music(paths))
                    self.download_thread.progress_percent.connect(lambda value: self.ui.progress_bar.setValue(int(value)))
                    self.download_thread.progress.connect(print)  # connect the signal to print messages
                    # TODO: make it output to status box
                    self.download_thread.error.connect(lambda msg: print("Error:", msg))
                    # TODO: make it output to status box

                    self.download_thread.start()  # starts the thread (calls run() internally)
                else:
                    self.ui.start_button.setEnabled(True)
                    self.ui.source_chooser.setEnabled(True)
                    self.ui.output_directory_button.setEnabled(True)
        except:
            pass
            #TODO

    def start_next_thread(self):
        try:
            path = next(self.music_remover_threads)
            self.music_remover_thread = MusicRemoverThread(path, self.user_output)

            self.music_remover_thread.completed.connect(self.start_next_thread)
            self.music_remover_thread.progress_percent.connect(lambda value: self.ui.progress_bar.setValue(int(value)))
            self.music_remover_thread.progress.connect(print)  # connect the signal to print messages
            # TODO: make it output to status box
            self.music_remover_thread.error.connect(lambda msg: print("Error:", msg))
            # TODO: make it output to status box
            self.music_remover_thread.start()


        except StopIteration:
            print("All files processed")
            self.ui.start_button.setEnabled(True)
            self.ui.source_chooser.setEnabled(True)
            self.ui.output_directory_button.setEnabled(True)
            shutil.rmtree(get_temp_path())
            # TODO: make it output to status box
            return


class LinkDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_linkDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

    def get_link(self):
        return self.ui.link_box.text()

    def get_quality(self):
        return self.ui.quality_selector.currentText()

    def get_is_remove_music(self):
        return self.ui.remove_music_box.isChecked()



def window():
    app = QApplication(sys.argv)
    win = MyWindow()

    shutil.rmtree(get_temp_path())

    win.show()
    sys.exit(app.exec())


window()

