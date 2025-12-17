import os
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import demucs.separate
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from .temp_utils import get_temp_path, get_resource_path


class MusicRemoverThread(QThread):
	progress = pyqtSignal(str)  # for status updates
	progress_percent = pyqtSignal(float)  # for progress bar
	error = pyqtSignal(str)
	completed = pyqtSignal(bool)  # path of seperated audio and video

	def __init__(self, input_video, user_output : Path):
		super().__init__()
		self.input_video = input_video
		self.user_output = user_output

	def run(self):
		# this method executes when the thread starts
		from logic.ffmpeg_utils import split_video

		try:
			output_dir = get_temp_path()
			base_name = self.input_video.stem

			output_audio = output_dir / f"{base_name}_AUDIO.wav"
			output_video = output_dir / f"{base_name}_VIDEO.mp4"

			self.progress.emit(f"Splitting {self.input_video}")
			split_video(self.input_video, output_audio, output_video)
			self.progress.emit(f"Finished Splitting {self.input_video}")  # send a message back to GUI

			model_path = get_resource_path(".models")

			model_name = "htdemucs"

			cmd = [
				"-n", model_name,
				str(output_audio),
				"-o", str(output_dir),
			]

			try:
				demucs.separate.main(cmd)

			except Exception as e:
				if "CUDA out of memory" in str(e):
					print("GPU memory error detected. Retrying on CPU...")
					cmd = ["-d", "cpu"] + cmd
					demucs.separate.main(cmd)

				else:
					print("Demucs failed:", e)
					raise

			output_audio.unlink()

			child_dir = next((output_dir / model_name).iterdir())
			final_audio = child_dir / "vocals.wav"

			from logic.ffmpeg_utils import combine_video

			self.progress.emit(f"Combining {self.input_video}")
			combine_video(final_audio, output_video, self.user_output)
			self.progress.emit(f"Finished Combining {final_audio} and {output_video} to {self.user_output}")

			self.completed.emit(True)

		except Exception as e:
			self.error.emit("Splitting Error: " + str(e))

