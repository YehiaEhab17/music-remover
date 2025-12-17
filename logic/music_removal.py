from pathlib import Path


from PyQt6.QtCore import QThread, pyqtSignal, pyqtBoundSignal
from audio_separator.separator import Separator

from .temp_utils import get_temp_path


class MusicRemoverThread(QThread):
    progress: pyqtBoundSignal = pyqtSignal(str)
    progress_percent: pyqtBoundSignal = pyqtSignal(float)
    error: pyqtBoundSignal = pyqtSignal(str)
    completed: pyqtBoundSignal = pyqtSignal(bool)

    def __init__(self, input_video: Path, user_output: Path) -> None:
        super().__init__()
        self.input_video: Path = input_video
        self.user_output: Path = user_output

    def run(self) -> None:
        from logic.ffmpeg_utils import split_video

        try:
            output_dir: Path = get_temp_path()
            base_name: str = self.input_video.stem

            output_audio: Path = output_dir / f"{base_name}_AUDIO.wav"
            output_video: Path = output_dir / f"{base_name}_VIDEO.mp4"

            self.progress.emit(f"Splitting {self.input_video}")
            split_video(self.input_video, output_audio, output_video)
            self.progress.emit(f"Finished Splitting {self.input_video}")

            separator: Separator = Separator(output_dir=str(output_dir))
            separator.load_model("UVR-MDX-NET-Voc_FT.onnx")

            output_files: list[str] = separator.separate(str(output_audio))
            output_audio.unlink()

            final_audio_path: Path = output_dir / Path(output_files[1])

            from logic.ffmpeg_utils import combine_video

            self.progress.emit(f"Combining {self.input_video}")
            combine_video(final_audio_path, output_video, self.user_output)
            self.progress.emit(f"Finished Combining {final_audio_path} and {output_video} to {self.user_output}")

            self.completed.emit(True)

        except Exception as e:
            self.error.emit("Splitting Error: " + str(e))
