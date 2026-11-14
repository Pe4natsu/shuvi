from pathlib import Path

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QWidget,
)

from shuvi.constant import APP_NAME
from shuvi.core.yt import DEFAULT_FILE_FORMAT, FILE_FORMATS
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
        self.setObjectName("form")
        self.setProperty("role", "card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)  # lets the stylesheet paint this QWidget
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(14)

        self.url = QLineEdit(self)
        layout.addRow("URL", self.url)

        self.folder = FolderSelectorWidget(self)
        layout.addRow("Output Folder", self.folder)

        self.profile = FolderSelectorWidget(self)
        layout.addRow("Web Profile", self.profile)

        self.file_format = QButtonGroup(self)
        formats_layout = QHBoxLayout()
        formats_layout.setSpacing(20)
        for name in FILE_FORMATS:
            button = QRadioButton(name, self)
            button.setChecked(name == DEFAULT_FILE_FORMAT)
            self.file_format.addButton(button)
            formats_layout.addWidget(button)
        formats_layout.addStretch()
        layout.addRow("Format", formats_layout)

        self.download_btn = QPushButton("Download", self)
        self.download_btn.setProperty("role", "primary")
        self.download_btn.clicked.connect(self.download)
        layout.addWidget(self.download_btn)

    def download(self):
        """Queue a download of the current URL to the output folder, in the chosen format."""
        url = self.url.text().strip()
        folder = self.folder.text().strip()
        video_id, playlist_id = parse_youtube_url(url)
        if not (video_id or playlist_id) or not folder:
            QMessageBox.warning(self, APP_NAME, "Enter a YouTube URL and an output folder.")
            return

        checked = self.file_format.checkedButton()
        file_format = checked.text() if checked else DEFAULT_FILE_FORMAT
        logger.info("Queueing %s as %s to %s", url, file_format, folder)
        profile = self.profile.text().strip() or None
        self.download_requested.emit(
            Download(url, Path(folder), profile, playlist=playlist_id is not None, file_format=file_format)
        )


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ShuviForm()
    w.show()
    sys.exit(app.exec())
