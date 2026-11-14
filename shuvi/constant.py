import sys
from pathlib import Path

APP_NAME = "Shuvi"

LOG_FORMAT = "[%(asctime)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Bundled tools (ffmpeg, ffprobe, deno): unpacked under sys._MEIPASS by PyInstaller, else the repo's bin folder
BIN_FOLDER = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent)) / "bin"
