import sys

from qtpy.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QTabWidget, QWidget

from shuvi.constant import APP_NAME
from shuvi.ui.form import ShuviForm
from shuvi.ui.video import VideoWidget


class DownloadWindow(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QHBoxLayout(self)

        self.form = ShuviForm(self)
        layout.addWidget(self.form)

        self.video = VideoWidget(self)
        layout.addWidget(self.video, stretch=1)

        self.form.url.textChanged.connect(self.video.set_url)


class Shuvi(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)

        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)

        dl_window = DownloadWindow(self)
        tabs.addTab(dl_window, "Download")


def main():
    app = QApplication(sys.argv)
    window = Shuvi()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
