from PyQt6.QtWidgets import QDialog

from GUI.dialog import Ui_linkDialog
from config import QUALITY_INDEX


class LinkDialog(QDialog):
    def __init__(
        self, default_quality: str = "720p", default_remove_music: bool = True
    ) -> None:
        super().__init__()
        self.ui = Ui_linkDialog()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())

        self.ui.remove_music_box.setChecked(default_remove_music)

        idx = QUALITY_INDEX.get(default_quality, 4)
        self.ui.quality_selector.setCurrentIndex(idx)

    def get_links(self) -> list[str]:
        text = self.ui.links_box.toPlainText()
        return [url.strip() for url in text.split() if url.strip()]

    def get_quality(self) -> str:
        return self.ui.quality_selector.currentText()

    def get_is_remove_music(self) -> bool:
        return self.ui.remove_music_box.isChecked()
