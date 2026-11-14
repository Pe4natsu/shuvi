from pathlib import Path
from string import Template

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont, QIcon, QPalette
from qtpy.QtWidgets import QApplication, QWidget

# Warm graphite surfaces with an orchid purple accent.
COLORS = {
    "bg": "#141311",
    "surface": "#1c1a17",
    "raised": "#25221e",
    "hover": "#2e2a25",
    "border": "#2f2b26",
    "border_strong": "#463f37",
    "text": "#ece6da",
    "text_muted": "#9c958a",
    "text_faint": "#6b655c",
    "accent": "#b36bdb",
    "accent_hover": "#c385e6",
    "accent_pressed": "#9853c0",
    "accent_soft": "#3d2c42",
    "on_accent": "#170d1c",
    "success": "#9bb57a",
    "warning": "#d9a441",
    "error": "#e0574a",
    "error_soft": "#3a1f1b",
}
FONT_FAMILIES = ["Segoe UI Variable Text", "Segoe UI"]
FONT_POINT_SIZE = 10
STYLESHEET_PATH = Path(__file__).with_name("theme.qss")
ICON_PATH = Path(__file__).with_name("assets") / "icon.ico"  # made from assets/icon.svg

PALETTE_ROLES = {
    QPalette.ColorRole.Window: "bg",
    QPalette.ColorRole.WindowText: "text",
    QPalette.ColorRole.Base: "surface",
    QPalette.ColorRole.AlternateBase: "raised",
    QPalette.ColorRole.Text: "text",
    QPalette.ColorRole.Button: "raised",
    QPalette.ColorRole.ButtonText: "text",
    QPalette.ColorRole.Highlight: "accent",
    QPalette.ColorRole.HighlightedText: "on_accent",
    QPalette.ColorRole.ToolTipBase: "raised",
    QPalette.ColorRole.ToolTipText: "text",
    QPalette.ColorRole.PlaceholderText: "text_faint",
    QPalette.ColorRole.Link: "accent",
}
DISABLED_ROLES = (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText)


def palette() -> QPalette:
    """Qt palette matching the stylesheet, for what QSS does not reach (dialogs, native parts)."""
    result = QPalette()
    for role, color in PALETTE_ROLES.items():
        result.setColor(role, QColor(COLORS[color]))
    for role in DISABLED_ROLES:
        result.setColor(QPalette.ColorGroup.Disabled, role, QColor(COLORS["text_faint"]))
    return result


def apply(app: QApplication) -> None:
    """Give the whole app the dark theme; call it before creating any window."""
    app.setStyle("Fusion")  # the most faithful base for stylesheets
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)  # dark Windows title bar
    app.setPalette(palette())
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPointSize(FONT_POINT_SIZE)
    app.setFont(font)
    app.setStyleSheet(Template(STYLESHEET_PATH.read_text(encoding="utf-8")).substitute(COLORS))


def set_style_property(widget: QWidget, name: str, value: str) -> None:
    """Set a property the stylesheet selects on, and restyle the widget to match."""
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
