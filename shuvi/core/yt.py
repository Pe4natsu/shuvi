from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yt_dlp
from dotenv import load_dotenv
from yt_dlp.utils import DownloadCancelled

from shuvi.log import YtDlpLogger, logger

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from yt_dlp import _Params
    from yt_dlp.extractor.common import _InfoDict

__all__ = ["DEFAULT_FILE_FORMAT", "FILE_FORMATS", "DownloadCancelled", "Progress", "Youtube", "download_fraction"]


@dataclass(frozen=True)
class FileFormat:
    """Yt-dlp options that produce one kind of output file."""

    options: _Params
    audio_only: bool = False


FILE_FORMATS: dict[str, FileFormat] = {
    "mp4": FileFormat({"format": "bestvideo*+bestaudio/best", "merge_output_format": "mp4"}),
    "mp3": FileFormat(
        {
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        },
        audio_only=True,
    ),
}
DEFAULT_FILE_FORMAT = "mp4"


@dataclass(frozen=True)
class Progress:
    """Progress of a running download."""

    fraction: float  # of the whole video or playlist, from 0 to 1
    speed: float | None  # bytes per second, for the file being downloaded
    eta: float | None  # seconds left for the file being downloaded


def download_fraction(status: Mapping[str, Any], *, audio_only: bool = False) -> float:
    """Fraction (0 to 1) of a whole video or playlist download reached at a yt-dlp progress status."""
    info = status.get("info_dict") or {}
    total_bytes = status.get("total_bytes") or status.get("total_bytes_estimate")
    if status.get("status") == "finished":
        file_fraction = 1.0
    elif total_bytes:
        file_fraction = min(status.get("downloaded_bytes", 0) / total_bytes, 1.0)
    else:
        file_fraction = 0.0

    # Best video quality is a video-only stream then an audio-only one, each counting for half of the video.
    if audio_only:
        video_fraction = file_fraction
    elif info.get("acodec") == "none":
        video_fraction = file_fraction / 2
    elif info.get("vcodec") == "none":
        video_fraction = (1 + file_fraction) / 2
    else:
        video_fraction = file_fraction

    position = (info.get("playlist_autonumber") or 1) - 1
    return (position + video_fraction) / (info.get("n_entries") or 1)


class Youtube:
    def __init__(
        self,
        output_folder: Path | None = None,
        profile: str | None = None,
        file_format: str = DEFAULT_FILE_FORMAT,
        on_progress: Callable[[Progress], None] | None = None,
        cancel_event: threading.Event | None = None,
    ):
        """Prepare downloads with the cookies of a Firefox profile.

        Args:
            output_folder: where to download (default: current folder); not needed to list a playlist.
            profile: Firefox profile path (default: WEB_PROFILE environment variable).
            file_format: a key of `FILE_FORMATS`, e.g. "mp4" or "mp3".
            on_progress: called with the `Progress` of the running download.
            cancel_event: set it from any thread to stop the running download with `DownloadCancelled`.

        """
        load_dotenv()
        self.profile = profile or os.environ["WEB_PROFILE"]
        self.output_folder = Path(output_folder) if output_folder else Path.cwd()
        if output_folder:
            self.output_folder.mkdir(parents=True, exist_ok=True)
        self.file_format = file_format
        self.on_progress = on_progress
        self.cancel_event = cancel_event or threading.Event()

    def base_options(self) -> _Params:
        return {
            **FILE_FORMATS[self.file_format].options,
            "cookiesfrombrowser": ("firefox", self.profile),  # (browser, profile path)
            "quiet": False,
            "no_warnings": True,
            "ignoreerrors": True,
            "retries": 10,
            "fragment_retries": 10,
            "js_runtimes": {"deno": {}},  # solves YouTube's JS challenges, without which streams return 403
            "extractor_retries": 5,
            "sleep_interval_requests": 1,
            "sleep_interval": 5,
            "max_sleep_interval": 15,
            "logger": YtDlpLogger(),
            "progress_hooks": [self.on_download_progress],
            "postprocessor_hooks": [self.on_postprocess],
            "match_filter": self.stop_if_cancelled,
        }

    def raise_if_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise DownloadCancelled

    def on_download_progress(self, status: Mapping[str, Any]) -> None:
        self.raise_if_cancelled()
        if self.on_progress:
            fraction = download_fraction(status, audio_only=FILE_FORMATS[self.file_format].audio_only)
            self.on_progress(Progress(fraction, status.get("speed"), status.get("eta")))

    def on_postprocess(self, status: Mapping[str, Any]) -> None:  # noqa: ARG002 - signature set by yt-dlp
        self.raise_if_cancelled()

    def stop_if_cancelled(self, info: Mapping[str, Any], *, incomplete: bool = False) -> str | None:  # noqa: ARG002 - signature set by yt-dlp
        """Yt-dlp match filter that never skips a video but checks for cancellation before each one."""
        self.raise_if_cancelled()
        return None

    def fetch_title(self, url: str) -> str:
        """Title of a video or playlist, without downloading it ("" if it cannot be read)."""
        options: _Params = {
            **self.base_options(),
            "extract_flat": "in_playlist",
            "playlistend": 1,  # a playlist's title does not need all of its entries
            "logger": YtDlpLogger(quiet=True),
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        return (info.get("title") or "") if info else ""

    def list_playlist(self, url: str) -> list[_InfoDict]:
        options: _Params = {**self.base_options(), "extract_flat": "in_playlist", "logger": YtDlpLogger(quiet=True)}
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:  # with "ignoreerrors", yt-dlp returns None instead of raising
            logger.warning("Could not read playlist %s", url)
            return []

        entries: list[_InfoDict] = [e for e in (info.get("entries") or []) if e]
        logger.info("Playlist '%s': %d video(s).", info.get("title"), len(entries))

        return entries

    def download_playlist(self, url: str) -> bool:
        """Download every video of a playlist; return False if any of them failed."""
        entries = self.list_playlist(url)
        total = len(entries)

        options: _Params = {
            **self.base_options(),
            "outtmpl": str(self.output_folder / "%(playlist_index)03d - %(title)s.%(ext)s"),
            "noplaylist": False,
            # skip what's already downloaded, per format so an mp3 run does not skip videos fetched as mp4
            "download_archive": str(self.output_folder / f"downloaded_{self.file_format}.txt"),
        }

        logger.info("Downloading %d video(s) as %s to %s", total, self.file_format, self.output_folder)
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.download([url]) == 0

    def download_video(self, url: str) -> bool:
        """Download only the video of a URL, even if it is part of a playlist; return False if it failed."""
        options: _Params = {
            **self.base_options(),
            "outtmpl": str(self.output_folder / "%(title)s.%(ext)s"),
            "noplaylist": True,
        }
        logger.info("Downloading %s as %s to %s", url, self.file_format, self.output_folder)
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.download([url]) == 0


if __name__ == "__main__":
    output_folder = Path(__file__).parent.parent.parent / "downloads" / "Test"
    youtube = Youtube(output_folder=output_folder)
    youtube.download_video(url="https://www.youtube.com/watch?v=MCYm453CE6Y")
