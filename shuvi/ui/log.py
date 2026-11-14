import contextlib
import logging

from qtpy.QtCore import QObject, Signal
from qtpy.QtGui import QColor, QTextCharFormat, QTextCursor
from qtpy.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from shuvi.constant import LOG_DATE_FORMAT, LOG_FORMAT
from shuvi.log import is_progress, logger
from shuvi.ui.theme import COLORS

# From the most to the least severe; less severe records keep the app's text color.
LEVEL_COLORS = ((logging.ERROR, COLORS["error"]), (logging.WARNING, COLORS["warning"]))
MAX_LINES = 5000


class LogSignal(QObject):
    """Carries log records from any thread to the GUI thread."""

    logged = Signal(int, str)  # level, formatted message


class SignalLogHandler(logging.Handler):
    """Logging handler that sends each record through a Qt signal."""

    def __init__(self):
        super().__init__()
        self.signal = LogSignal()
        self.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        self.addFilter(lambda record: not is_progress(record))  # the queue already shows the progress

    def emit(self, record: logging.LogRecord) -> None:
        with contextlib.suppress(RuntimeError):  # the signal object is already deleted while the app quits
            self.signal.logged.emit(record.levelno, self.format(record))


class LogWidget(QWidget):
    """Shows the app's log, colored by level, with a button to clear it."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.view = QPlainTextEdit(self)
        self.view.setObjectName("logView")
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(MAX_LINES)
        layout.addWidget(self.view)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self.view.clear)
        buttons.addWidget(self.clear_btn)
        layout.addLayout(buttons)

        self.formats = {level: self.text_format(color) for level, color in LEVEL_COLORS}
        self.default_format = QTextCharFormat()

        self.handler = SignalLogHandler()
        self.handler.signal.logged.connect(self.append)
        logger.addHandler(self.handler)

    @staticmethod
    def text_format(color: str) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        return text_format

    def format_for(self, level: int) -> QTextCharFormat:
        return next((self.formats[threshold] for threshold, _ in LEVEL_COLORS if level >= threshold), self.default_format)

    def append(self, level: int, message: str) -> None:
        """Add a message at the end, following it only if the view was already scrolled to the bottom."""
        scroll_bar = self.view.verticalScrollBar()
        at_bottom = scroll_bar.value() == scroll_bar.maximum()

        cursor = QTextCursor(self.view.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.view.document().isEmpty():
            cursor.insertBlock()
        cursor.insertText(message, self.format_for(level))

        if at_bottom:
            scroll_bar.setValue(scroll_bar.maximum())
