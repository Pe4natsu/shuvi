from qtpy.QtWidgets import QFormLayout, QLineEdit, QPushButton, QWidget

from shuvi.log import logger
from shuvi.ui.widgets import FolderSelectorWidget


class ShuviForm(QWidget):
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
        logger.info("Downloading %s to %s", self.url.text(), self.folder.text())


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ShuviForm()
    w.show()
    sys.exit(app.exec())
