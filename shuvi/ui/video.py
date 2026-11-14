import html
import re
from urllib.parse import parse_qs, urlparse

from qtpy.QtCore import Qt, QTimer, QUrl
from qtpy.QtWebEngineWidgets import QWebEngineView  # pyright: ignore[reportPrivateImportUsage]
from qtpy.QtWidgets import QHBoxLayout, QLabel, QStackedLayout, QWidget

from shuvi.ui.playlist import PlaylistWidget

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]+$")

# YouTube refuses to play an embed that has no HTTP Referer ("Error 153"), so instead of
# opening the embed URL directly, it is put in an iframe of a page served from an https origin.
PLAYER_BASE_URL = QUrl("https://localhost/")
PLAYER_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; background: #000; }
  iframe { border: 0; width: 100%; height: 100%; }
</style>
</head>
<body>
<iframe src="__SRC__" allow="autoplay; encrypted-media; picture-in-picture"
        referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
</body>
</html>"""


# Asks YouTube's player (inside the iframe) which video it is playing.
CURRENT_VIDEO_JS = """(() => {
  const player = document.getElementById("movie_player");
  return player && player.getVideoData ? player.getVideoData().video_id : null;
})()"""


def parse_youtube_url(url: str) -> tuple[str | None, str | None]:
    """Return the (video id, playlist id) of a YouTube video, shorts or playlist URL.

    Either one is None if missing, or if the text is not (yet) a complete YouTube URL.
    """
    url = url.strip()
    if not url:
        return None, None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").removeprefix("www.").removeprefix("m.").removeprefix("music.")
    query = parse_qs(parsed.query)

    video_id = ""
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "youtube-nocookie.com"):
        parts = parsed.path.strip("/").split("/")
        if parts[0] == "watch":
            video_id = query.get("v", [""])[0]
        elif len(parts) > 1 and parts[0] in ("shorts", "embed", "live", "v"):
            video_id = parts[1]
    else:
        return None, None

    playlist_id = query.get("list", [""])[0]
    return (
        video_id if VIDEO_ID.match(video_id) else None,
        playlist_id if PLAYLIST_ID.match(playlist_id) else None,
    )


def embed_url(video_id: str | None, playlist_id: str | None) -> str | None:
    """URL of YouTube's embedded player for a video, a playlist, or a video within a playlist."""
    list_param = f"?list={playlist_id}" if playlist_id else ""
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}{list_param}"
    if playlist_id:
        return f"https://www.youtube.com/embed/videoseries{list_param}"
    return None


class VideoWidget(QWidget):
    """Plays the YouTube video of a URL with YouTube's embedded player.

    For a playlist URL, the videos of the playlist are listed at the right of the player.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedLayout()
        layout.addLayout(self.stack, stretch=2)

        self.placeholder = QLabel("Enter a YouTube URL to watch the video here", self)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.stack.addWidget(self.placeholder)

        self.player = QWebEngineView(self)
        self.player.setMinimumSize(480, 270)
        self.stack.addWidget(self.player)

        self.playlist = PlaylistWidget(self)
        self.playlist.video_selected.connect(self.play_from_playlist)
        layout.addWidget(self.playlist, stretch=1)

        self.url = ""
        self.loaded: tuple[str | None, str | None] = (None, None)  # (video id, playlist id)

        # Wait until the user stops typing before (re)loading the player.
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(500)
        self.debounce.timeout.connect(self.refresh)

        # YouTube moves to the next video by itself: check regularly which one is playing.
        self.current_video_poll = QTimer(self)
        self.current_video_poll.setInterval(1000)
        self.current_video_poll.timeout.connect(self.poll_current_video)

    def set_url(self, url: str):
        self.url = url
        self.debounce.start()

    def refresh(self) -> None:
        video_id, playlist_id = parse_youtube_url(self.url)
        if (video_id, playlist_id) == self.loaded:
            return
        self.play(video_id, playlist_id)
        self.playlist.load(playlist_id)

    def play(self, video_id: str | None, playlist_id: str | None) -> None:
        self.loaded = (video_id, playlist_id)
        src = embed_url(video_id, playlist_id)

        if src is None:
            self.player.setUrl(QUrl("about:blank"))  # stops the current video
            self.stack.setCurrentWidget(self.placeholder)
        else:
            self.player.setHtml(PLAYER_HTML.replace("__SRC__", html.escape(src)), PLAYER_BASE_URL)
            self.stack.setCurrentWidget(self.player)

        self.playlist.set_current(video_id)
        if playlist_id:
            self.current_video_poll.start()
        else:
            self.current_video_poll.stop()

    def play_from_playlist(self, video_id: str) -> None:
        self.play(video_id, self.playlist.playlist_id)

    def poll_current_video(self) -> None:
        iframes = self.player.page().mainFrame().children()
        if iframes:
            iframes[0].runJavaScript(CURRENT_VIDEO_JS, 0, self.on_current_video)

    def on_current_video(self, video_id: object) -> None:
        if isinstance(video_id, str) and video_id and video_id != self.playlist.current_video_id:
            self.playlist.set_current(video_id)


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = VideoWidget()
    w.resize(960, 360)
    w.set_url("https://www.youtube.com/watch?v=MCYm453CE6Y&list=PLSJxVvV6iE8K4p5iHPO7naBlCKjncqtGH")
    w.show()
    sys.exit(app.exec())
