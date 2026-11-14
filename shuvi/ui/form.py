from pathlib import Path

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QFormLayout, QLineEdit, QMessageBox, QPushButton, QWidget

from shuvi.constant import APP_NAME
from shuvi.log import logger
from shuvi.ui.queues import Download
from shuvi.ui.video import parse_youtube_url
from shuvi.ui.widgets import FolderSelectorWidget


class ShuviForm(QWidget):
    download_requested = Signal(object)  # Download

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QFormLayout()
        self.setLayout(layout)
        self.setMinimumWidth(400)

        self.url = QLineEdit(self)
        layout.addRow("URL", self.url)

        self.folder = FolderSelectorWidget(self)
        layout.addRow("Output Folder", self.folder)

        self.profile = FolderSelectorWidget(self)
        layout.addRow("Web Profile", self.profile)

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download)
        layout.addWidget(self.download_btn)

    def download(self):
        """Queue a download of the current URL to the output folder."""
        url = self.url.text().strip()
        folder = self.folder.text().strip()
        video_id, playlist_id = parse_youtube_url(url)
        if not (video_id or playlist_id) or not folder:
            QMessageBox.warning(self, APP_NAME, "Enter a YouTube URL and an output folder.")
            return

        logger.info("Queueing %s to %s", url, folder)
        profile = self.profile.text().strip() or None
        self.download_requested.emit(Download(url, Path(folder), profile, playlist=playlist_id is not None))


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ShuviForm()
    w.show()
    sys.exit(app.exec())
