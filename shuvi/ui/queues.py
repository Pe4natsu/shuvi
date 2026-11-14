import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from pathlib import Path

from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from shuvi.core.yt import DEFAULT_FILE_FORMAT, DownloadCancelled, Progress, Youtube
from shuvi.log import logger
from shuvi.ui.playlist import format_duration

REPORT_INTERVAL = 0.5  # seconds between progress updates when the percent does not change
SPEED_UNITS = ("B/s", "KiB/s", "MiB/s", "GiB/s")
BYTES_PER_KIB = 1024
LONGEST_STATUS = "Downloading 100% · 999.9 MiB/s · ETA 00:00:00"  # sizes the status column


def format_speed(bytes_per_second: float) -> str:
    for unit in SPEED_UNITS[:-1]:
        if bytes_per_second < BYTES_PER_KIB:
            return f"{bytes_per_second:.1f} {unit}"
        bytes_per_second /= BYTES_PER_KIB
    return f"{bytes_per_second:.1f} {SPEED_UNITS[-1]}"


class Status(Enum):
    """State of a queued download, as shown to the user."""

    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    CANCELLING = "Cancelling..."
    CANCELLED = "Cancelled"
    DONE = "Done"
    ERRORS = "Finished with errors"
    FAILED = "Failed"

    @property
    def finished(self) -> bool:
        return self in FINISHED_STATUSES


FINISHED_STATUSES = frozenset({Status.CANCELLED, Status.DONE, Status.ERRORS, Status.FAILED})


@dataclass(eq=False)
class Download:
    """Parameters of a queued download, and the event that cancels it."""

    url: str
    output_folder: Path
    profile: str | None = None
    playlist: bool = False
    file_format: str = DEFAULT_FILE_FORMAT
    title: str = ""  # looked up from the URL in the background after queueing
    cancel_event: threading.Event = field(default_factory=threading.Event)


class DownloadWorker(QObject):
    """Runs the queued downloads one after another in a background thread."""

    titled = Signal(object)  # Download
    started = Signal(object)  # Download
    progressed = Signal(object, object)  # Download, Progress
    finished = Signal(object, object)  # Download, Status

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.pending: queue.Queue[Download | None] = queue.Queue()  # None wakes the thread up to stop it
        self.current: Download | None = None
        self.stopping = threading.Event()
        self.percent = 0
        self.reported_at = 0.0
        threading.Thread(target=self.run, daemon=True).start()

    def add(self, download: Download) -> None:
        self.pending.put(download)
        # Own thread: the title must not wait for the downloads queued before this one.
        threading.Thread(target=self.fetch_title, args=(download,), daemon=True).start()

    def fetch_title(self, download: Download) -> None:
        try:
            title = Youtube(profile=download.profile).fetch_title(download.url)
        except Exception:  # noqa: BLE001 - the row keeps showing the URL instead
            logger.exception("Could not read the title of %s", download.url)
            return
        if title and not self.stopping.is_set():
            download.title = title
            self.titled.emit(download)

    def stop(self) -> None:
        """Cancel the running download and end the thread, without emitting any more signals."""
        self.stopping.set()
        if self.current:
            self.current.cancel_event.set()
        self.pending.put(None)

    def run(self) -> None:
        while not self.stopping.is_set():
            download = self.pending.get()
            if download is None or download.cancel_event.is_set():
                continue  # stopping, or cancelled while it was pending
            self.current = download
            self.started.emit(download)
            status = self.process(download)
            if not self.stopping.is_set():
                self.finished.emit(download, status)

    def process(self, download: Download) -> Status:
        self.percent = 0
        try:
            youtube = Youtube(
                download.output_folder,
                download.profile,
                file_format=download.file_format,
                on_progress=partial(self.report_progress, download),
                cancel_event=download.cancel_event,
            )
            download_method = youtube.download_playlist if download.playlist else youtube.download_video
            completed = download_method(download.url)
        except DownloadCancelled:
            return Status.CANCELLED
        except Exception:  # noqa: BLE001 - an uncaught error would kill the worker and block the queue
            logger.exception("Could not download %s", download.url)
            return Status.FAILED
        return Status.DONE if completed else Status.ERRORS

    def report_progress(self, download: Download, progress: Progress) -> None:
        """Forward yt-dlp's progress, which comes many times per second, only when it is worth a redraw."""
        percent = int(progress.fraction * 100)
        now = time.monotonic()
        is_due = percent != self.percent or now - self.reported_at >= REPORT_INTERVAL
        if is_due and not self.stopping.is_set():
            self.percent, self.reported_at = percent, now
            self.progressed.emit(download, progress)


class QueueRow(QWidget):
    """One download of the queue: its URL and folder, its status, and a button to cancel or remove it."""

    cancel_requested = Signal(object)  # Download

    def __init__(self, download: Download, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.download = download
        self.status = Status.PENDING
        self.percent = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.description = QLabel(self)
        # Cut long titles instead of widening the window.
        self.description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.description, stretch=1)

        self.status_label = QLabel(self)
        self.status_label.setMinimumWidth(self.status_label.fontMetrics().horizontalAdvance(LONGEST_STATUS))
        layout.addWidget(self.status_label)

        self.cancel_btn = QToolButton(self)
        self.cancel_btn.setText("✕")
        self.cancel_btn.setAutoRaise(True)
        self.cancel_btn.clicked.connect(self.request_cancel)
        layout.addWidget(self.cancel_btn)

        self.show_description()
        self.set_status(Status.PENDING)

    def show_description(self) -> None:
        """Show the title (or the URL until it is known), the file format and the output folder."""
        name = self.download.title or self.download.url
        self.description.setText(f"{name} ({self.download.file_format})  ->  {self.download.output_folder}")
        self.description.setToolTip(f"{name}\n{self.download.url}\n{self.download.output_folder}")

    def set_status(self, status: Status, percent: int | None = None) -> None:
        self.status = status
        if status.finished:
            self.percent = 100
        elif percent is not None:
            self.percent = percent
        is_downloading = status is Status.DOWNLOADING
        self.status_label.setText(f"{status.value} {self.percent}%" if is_downloading else status.value)
        self.cancel_btn.setToolTip("Remove from the queue" if status.finished else "Cancel the download")
        self.cancel_btn.setEnabled(status is not Status.CANCELLING)

    def show_progress(self, progress: Progress) -> None:
        self.set_status(Status.DOWNLOADING, int(progress.fraction * 100))
        parts = [self.status_label.text()]
        if progress.speed:
            parts.append(format_speed(progress.speed))
        if progress.eta is not None:
            parts.append(f"ETA {format_duration(progress.eta)}")
        self.status_label.setText(" · ".join(parts))

    def request_cancel(self) -> None:
        self.cancel_requested.emit(self.download)


class QueueWidget(QWidget):
    """Download queue: an overall progress bar above one row per download."""

    active_count_changed = Signal(int)  # downloads not finished yet

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        rows_container = QWidget(self)
        self.rows_layout = QVBoxLayout(rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.addStretch()  # keeps the rows at the top
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(rows_container)
        layout.addWidget(scroll_area)

        self.rows: dict[Download, QueueRow] = {}
        self.worker = DownloadWorker(self)
        self.worker.titled.connect(self.on_titled)
        self.worker.started.connect(self.on_started)
        self.worker.progressed.connect(self.on_progressed)
        self.worker.finished.connect(self.on_finished)
        self.refresh()

    def add(self, download: Download) -> None:
        row = QueueRow(download, self)
        row.cancel_requested.connect(self.cancel)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)  # before the stretch
        self.rows[download] = row
        self.worker.add(download)
        self.refresh()

    def cancel(self, download: Download) -> None:
        download.cancel_event.set()
        row = self.rows[download]
        if row.status is Status.DOWNLOADING:
            row.set_status(Status.CANCELLING)  # removed once yt-dlp has stopped
        else:
            self.remove(download)

    def remove(self, download: Download) -> None:
        self.rows.pop(download).deleteLater()
        self.refresh()

    def on_titled(self, download: Download) -> None:
        if row := self.rows.get(download):
            row.show_description()

    def on_started(self, download: Download) -> None:
        if row := self.rows.get(download):
            row.set_status(Status.DOWNLOADING, 0)
            self.refresh()

    def on_progressed(self, download: Download, progress: Progress) -> None:
        row = self.rows.get(download)
        if row and row.status is Status.DOWNLOADING:
            row.show_progress(progress)
            self.refresh()

    def on_finished(self, download: Download, status: Status) -> None:
        if download not in self.rows:
            return
        if status is Status.CANCELLED:
            self.remove(download)
        else:
            self.rows[download].set_status(status)
            self.refresh()

    def refresh(self) -> None:
        """Update the overall progress bar and the number of active downloads."""
        rows = list(self.rows.values())
        finished = sum(row.status.finished for row in rows)
        self.progress_bar.setValue(sum(row.percent for row in rows) // len(rows) if rows else 0)
        self.progress_bar.setFormat(f"{finished}/{len(rows)} downloads done - %p%" if rows else "No downloads")
        self.active_count_changed.emit(len(rows) - finished)
