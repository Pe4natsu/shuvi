import html
import re
from urllib.parse import parse_qs, urlparse

from qtpy.QtCore import Qt, QTimer, QUrl
# qtpy re-imports this class by name, which Pylance misreads as a private import.
from qtpy.QtWebEngineWidgets import QWebEngineView  # pyright: ignore[reportPrivateImportUsage]
from qtpy.QtWidgets import QLabel, QStackedLayout, QWidget

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]+$")

# YouTube refuses to play an embed that has no HTTP Referer ("Error 153"), so instead of
# opening the embed URL directly, it is put in an iframe of a page served from an https origin.
_PLAYER_BASE_URL = QUrl("https://localhost/")
_PLAYER_HTML = """<!doctype html>
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


def embed_url(url: str) -> str | None:
    """Turn a YouTube video, shorts or playlist URL into the URL of its embedded player.

    Returns None if the text is not (yet) a complete YouTube URL.
    """
    url = url.strip()
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").removeprefix("www.").removeprefix("m.").removeprefix("music.")
    query = parse_qs(parsed.query)

    video_id = None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "youtube-nocookie.com"):
        parts = parsed.path.strip("/").split("/")
        if parts[0] == "watch":
            video_id = query.get("v", [""])[0]
        elif len(parts) > 1 and parts[0] in ("shorts", "embed", "live", "v"):
            video_id = parts[1]
    else:
        return None

    playlist = query.get("list", [""])[0]
    list_param = f"?list={playlist}" if _PLAYLIST_ID.match(playlist) else ""

    if video_id and _VIDEO_ID.match(video_id):
        return f"https://www.youtube.com/embed/{video_id}{list_param}"
    if list_param:
        return f"https://www.youtube.com/embed/videoseries{list_param}"
    return None


class VideoWidget(QWidget):
    """Plays the YouTube video (or playlist) of a URL, using YouTube's embedded player."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self._stack = QStackedLayout(self)

        self.placeholder = QLabel("Enter a YouTube URL to watch the video here", self)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        self._stack.addWidget(self.placeholder)

        self.player = QWebEngineView(self)
        self.player.setMinimumSize(320, 180)  # 16:9
        self._stack.addWidget(self.player)

        self._url = ""
        self._loaded_src: str | None = None

        # Wait until the user stops typing before (re)loading the player.
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(500)
        self._debounce.timeout.connect(self._refresh)

    def set_url(self, url: str):
        self._url = url
        self._debounce.start()

    def _refresh(self) -> None:
        src = embed_url(self._url)
        if src == self._loaded_src:
            return
        self._loaded_src = src

        if src is None:
            self.player.setUrl(QUrl("about:blank"))  # stops the current video
            self._stack.setCurrentWidget(self.placeholder)
        else:
            self.player.setHtml(_PLAYER_HTML.replace("__SRC__", html.escape(src)), _PLAYER_BASE_URL)
            self._stack.setCurrentWidget(self.player)


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = VideoWidget()
    w.resize(640, 360)
    w.set_url("https://www.youtube.com/watch?v=MCYm453CE6Y")
    w.show()
    sys.exit(app.exec())
