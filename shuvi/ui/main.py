import sys

from qtpy.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from shuvi.constant import APP_NAME
from shuvi.ui.form import ShuviForm
from shuvi.ui.video import VideoWidget


class ShuviWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)

        central = QWidget(self)
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        self.form = ShuviForm(central)
        layout.addWidget(self.form, stretch=1)

        self.video = VideoWidget(central)
        layout.addWidget(self.video, stretch=1)

        self.form.url.textChanged.connect(self.video.set_url)


def main():
    app = QApplication(sys.argv)
    window = ShuviWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
