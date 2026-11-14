import threading

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from shuvi.core.yt import Youtube
from shuvi.log import logger


def format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class PlaylistWidget(QWidget):
    """Lists the videos of a YouTube playlist; clicking one emits `video_selected`."""

    video_selected = Signal(str)  # video id
    entries_loaded = Signal(str, object)  # playlist id, list of entries (None if it failed)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.header = QLabel(self)
        self.header.setProperty("role", "caption")
        layout.addWidget(self.header)

        self.list = QListWidget(self)
        self.list.setMinimumWidth(400)
        # Cut long titles with "..." instead of scrolling sideways (the tooltip shows the full title).
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list)

        self.playlist_id: str | None = None
        self.current_video_id: str | None = None
        self.entries_loaded.connect(self.show_entries)
        self.hide()

    def load(self, playlist_id: str | None) -> None:
        """Show the videos of a playlist, or hide the widget if `playlist_id` is None."""
        if playlist_id == self.playlist_id:
            return
        self.playlist_id = playlist_id
        self.list.clear()
        if playlist_id is None:
            self.hide()
            return

        self.header.setText("Loading playlist...")
        self.show()
        # yt-dlp takes a few seconds: run it in a thread so the window does not freeze.
        threading.Thread(target=self.fetch, args=(playlist_id,), daemon=True).start()

    def fetch(self, playlist_id: str) -> None:
        """Fetch the playlist in a worker thread; the signal hands the result back to the GUI thread."""
        try:
            entries = Youtube().list_playlist(f"https://www.youtube.com/playlist?list={playlist_id}")
        except Exception:  # noqa: BLE001 - an uncaught error would leave the panel stuck on "Loading..."
            logger.exception("Could not load playlist %s", playlist_id)
            entries = None
        self.entries_loaded.emit(playlist_id, entries)

    def show_entries(self, playlist_id: str, entries: list | None) -> None:
        if playlist_id != self.playlist_id:
            return  # the URL changed while this playlist was loading
        if not entries:
            self.header.setText("Could not load the playlist" if entries is None else "Empty playlist")
            return

        self.header.setText(f"{len(entries)} videos")
        for index, entry in enumerate(entries, start=1):
            title = entry.get("title") or entry.get("id")
            duration = entry.get("duration")
            text = f"{index}. {title}" + (f"  ({format_duration(duration)})" if duration else "")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry.get("id"))
            item.setToolTip(text)
            self.list.addItem(item)
        self.set_current(self.current_video_id)

    def set_current(self, video_id: str | None) -> None:
        """Highlight the video being played (without emitting `video_selected`)."""
        self.current_video_id = video_id
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == video_id:
                self.list.setCurrentItem(item)
                self.list.scrollToItem(item)
                return
        self.list.clearSelection()

    def on_item_clicked(self, item: QListWidgetItem) -> None:
        self.video_selected.emit(item.data(Qt.ItemDataRole.UserRole))
