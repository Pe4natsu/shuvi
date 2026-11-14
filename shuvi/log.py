import logging
import re
import sys

from yt_dlp.utils import remove_terminal_sequences

from shuvi.constant import APP_NAME, LOG_DATE_FORMAT, LOG_FORMAT

__all__ = ["YtDlpLogger", "is_progress", "logger"]

# yt-dlp's live progress, e.g. "[download]  42.1% of 12.73MiB at 2.95MiB/s ETA 00:04"
PROGRESS_LINE = re.compile(r"^(\d+: )?\[download\]\s+[\d.]+%")


def is_progress(record: logging.LogRecord) -> bool:
    return getattr(record, "progress", False)


class ConsoleHandler(logging.StreamHandler):
    """Console handler that rewrites progress records on a single line, as yt-dlp does."""

    def __init__(self):
        super().__init__()
        self.on_progress_line = False

    def emit(self, record: logging.LogRecord) -> None:
        progress = is_progress(record)
        if self.on_progress_line and not progress:
            try:
                self.stream.write("\n")  # keep the last progress line instead of writing over it
            except Exception:  # noqa: BLE001 - logging must never raise into the caller
                self.handleError(record)
        self.terminator = "\r" if progress else "\n"
        self.on_progress_line = progress
        super().emit(record)


console_handlers = [ConsoleHandler()] if sys.stderr else []  # windowed exe has no stderr
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, handlers=console_handlers)

logger = logging.getLogger(APP_NAME)


class YtDlpLogger:
    """Forwards yt-dlp's messages to the app logger, so they reach every log handler."""

    def __init__(self, ydl: object = None, *, quiet: bool = False):  # noqa: ARG002 - signature set by yt-dlp
        self.quiet = quiet

    def debug(self, message: str) -> None:
        """Yt-dlp sends its screen messages and live progress here: log them as info unless quiet."""
        if message.startswith("[debug] "):
            logger.debug(message)
        elif not self.quiet:
            self.info(message)

    def info(self, message: str) -> None:
        text = remove_terminal_sequences(message).strip()
        logger.info(text, extra={"progress": bool(PROGRESS_LINE.match(text))})

    def warning(self, message: str, *, once: bool = False, only_once: bool = False) -> None:  # noqa: ARG002 - signature set by yt-dlp
        logger.warning(remove_terminal_sequences(message).strip())

    def error(self, message: str) -> None:
        logger.error(remove_terminal_sequences(message).strip())

    def stdout(self, message: str) -> None:
        self.info(message)

    def stderr(self, message: str) -> None:
        self.error(message)
