# PyInstaller build of the Shuvi app: `uv run pyinstaller shuvi.spec --noconfirm`, output in dist/Shuvi.
# bin/ must hold ffmpeg.exe and ffprobe.exe (and their DLLs for a "shared" ffmpeg build).
from pathlib import Path, PurePath

from deno import find_deno_bin

TOOLS_FOLDER = "bin"  # matches shuvi.constant.BIN_FOLDER inside the bundle
KEPT_WEBENGINE_LOCALES = {"en-US.pak"}  # Qt WebEngine falls back to en-US for the other languages

# Qt parts pulled in by PySide6's hooks that the app never uses, matched against bundled file paths.
UNUSED_QT_FILES = (
    "Qt63D",
    "Qt6Quick3D",
    "Qt6QuickControls2",
    "Qt6QuickDialogs2",
    "Qt6QuickTemplates2",
    "Qt6Graphs",
    "Qt6DataVisualization",
    "Qt6LabsStyleKit",
    "QtDataVisualization",
    "PySide6/qml/",
    "qtwebengine_devtools_resources",
    ".debug.",
)


def is_unused(destination: str) -> bool:
    path = PurePath(destination).as_posix()
    if "qtwebengine_locales/" in path:
        return PurePath(path).name not in KEPT_WEBENGINE_LOCALES
    if path.startswith("PySide6/translations/") and path.endswith(".qm"):
        return True
    return any(name in path for name in UNUSED_QT_FILES)


tools = [path for path in Path("bin").glob("*") if path.suffix in {".exe", ".dll"} and path.stem != "ffplay"]
if not any(path.stem == "ffmpeg" for path in tools):
    raise SystemExit("bin/ffmpeg.exe is missing: download ffmpeg into bin/ before building.")

a = Analysis(
    ["shuvi/ui/main.py"],
    pathex=["."],
    # As data, not binaries: copied as they are, without PyInstaller moving their DLLs out of bin/
    datas=[(str(path), TOOLS_FOLDER) for path in tools]
    + [(find_deno_bin(), TOOLS_FOLDER), ("shuvi/ui/theme.qss", "shuvi/ui")],
    excludes=["tkinter"],
)
a.binaries = [entry for entry in a.binaries if not is_unused(entry[0])]
a.datas = [entry for entry in a.datas if not is_unused(entry[0])]

pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Shuvi", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Shuvi")
