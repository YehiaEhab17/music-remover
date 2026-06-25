import torch
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from .settings import Ui_SettingsDialog
from logic import settings_manager
from logic.utils import get_temp_path, clear_temp_dir
from config import QUALITY_INDEX


CHUNK_INDEX = {30: 0, 60: 1, 120: 2}


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.ui.browse_output_button.clicked.connect(self._browse_output)
        self.ui.clear_cache_button.clicked.connect(self._clear_cache)
        self.ui.gpu_checkbox.toggled.connect(self._on_gpu_toggled)
        self._load_settings()
        self._apply_gpu_state()

    def _load_settings(self) -> None:
        current = settings_manager.load()
        self.ui.gpu_checkbox.setChecked(current["gpu_enabled"])
        self.ui.tensorrt_checkbox.setChecked(current["use_tensorrt"])
        self.ui.gpu_threads_spinbox.setValue(current["gpu_threads"])
        self.ui.chunking_checkbox.setChecked(current["chunking_enabled"])

        cidx = CHUNK_INDEX.get(current["chunk_duration_secs"], 1)
        self.ui.chunk_duration_combo.setCurrentIndex(cidx)

        self.ui.cpu_threads_spinbox.setValue(current["cpu_threads"])
        self.ui.retry_chunks_checkbox.setChecked(current["retry_failed_chunks"])

        qidx = QUALITY_INDEX.get(current["default_quality"], 4)
        self.ui.default_quality_combo.setCurrentIndex(qidx)

        self.ui.default_output_path.setText(current["default_output_path"])
        self.ui.remove_music_checkbox.setChecked(current["default_remove_music"])
        self.ui.benchmarking_checkbox.setChecked(current["benchmarking_enabled"])

    def _clear_cache(self) -> None:
        temp = get_temp_path()
        if not temp.exists() or not any(temp.iterdir()):
            QMessageBox.information(self, "Cache", "Cache is already empty.")
            return

        reply = QMessageBox.question(
            self,
            "Clear Cache",
            f"Delete all cached downloads and temporary files?\n\nLocation: {temp}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            clear_temp_dir()
            QMessageBox.information(self, "Cache", "Cache cleared successfully.")
        except OSError as e:
            QMessageBox.warning(self, "Cache", f"Failed to clear cache:\n{e}")

    def _apply_gpu_state(self) -> None:
        cuda_available = torch.cuda.is_available()
        self.ui.gpu_checkbox.setEnabled(cuda_available)
        if not cuda_available:
            self.ui.gpu_checkbox.setChecked(False)
            self.ui.gpu_status.setText("CUDA not available — falling back to CPU")
        self._on_gpu_toggled(self.ui.gpu_checkbox.isChecked())

    def _on_gpu_toggled(self, checked: bool) -> None:
        self.ui.tensorrt_checkbox.setEnabled(checked)
        self.ui.gpu_threads_label.setVisible(checked)
        self.ui.gpu_threads_spinbox.setVisible(checked)
        if not checked:
            self.ui.tensorrt_checkbox.setChecked(False)
            self.ui.gpu_threads_spinbox.setValue(1)

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose default output path")
        if directory:
            self.ui.default_output_path.setText(directory)

    def get_settings(self) -> dict:
        dur_text = self.ui.chunk_duration_combo.currentText()
        duration = int(dur_text.replace("s", ""))

        gpu_on = self.ui.gpu_checkbox.isChecked() and torch.cuda.is_available()

        return {
            "gpu_enabled": gpu_on,
            "use_tensorrt": self.ui.tensorrt_checkbox.isChecked() and gpu_on,
            "gpu_threads": self.ui.gpu_threads_spinbox.value() if gpu_on else 1,
            "chunking_enabled": self.ui.chunking_checkbox.isChecked(),
            "chunk_duration_secs": duration,
            "cpu_threads": self.ui.cpu_threads_spinbox.value(),
            "retry_failed_chunks": self.ui.retry_chunks_checkbox.isChecked(),
            "default_quality": self.ui.default_quality_combo.currentText(),
            "default_output_path": self.ui.default_output_path.text().strip(),
            "default_remove_music": self.ui.remove_music_checkbox.isChecked(),
            "benchmarking_enabled": self.ui.benchmarking_checkbox.isChecked(),
        }
