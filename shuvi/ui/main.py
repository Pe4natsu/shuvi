import sys

from qtpy.QtGui import QCloseEvent
from qtpy.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QTabWidget, QWidget

from shuvi.constant import APP_NAME
from shuvi.ui.form import ShuviForm
from shuvi.ui.log import LogWidget
from shuvi.ui import theme
from shuvi.ui.queues import QueueWidget
from shuvi.ui.video import VideoWidget


class DownloadWindow(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.form = ShuviForm(self)
        layout.addWidget(self.form)

        self.video = VideoWidget(self)
        layout.addWidget(self.video, stretch=1)

        self.form.url.textChanged.connect(self.video.set_url)


class Shuvi(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        dl_window = DownloadWindow(self)
        self.tabs.addTab(dl_window, "Download")

        self.queue = QueueWidget(self)
        self.tabs.addTab(self.queue, "Queue")

        self.log = LogWidget(self)
        self.tabs.addTab(self.log, "Log")

        dl_window.form.download_requested.connect(self.queue.add)
        self.queue.active_count_changed.connect(self.update_queue_tab)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.queue.worker.stop()
        super().closeEvent(event)

    def update_queue_tab(self, active_count: int) -> None:
        """Show the number of downloads not finished yet in the queue tab's title."""
        title = f"Queue ({active_count})" if active_count else "Queue"
        self.tabs.setTabText(self.tabs.indexOf(self.queue), title)


def main():
    app = QApplication(sys.argv)
    theme.apply(app)
    window = Shuvi()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
