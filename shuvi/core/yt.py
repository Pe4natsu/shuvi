from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import yt_dlp
from dotenv import load_dotenv

from shuvi.log import logger

if TYPE_CHECKING:
    from yt_dlp import _Params
    from yt_dlp.extractor.common import _InfoDict


class Youtube:
    def __init__(self, output_folder: Path | None = None, profile: str | None = None):
        """`output_folder` is only needed to download (default: current folder), not to list a playlist."""
        load_dotenv()
        self.profile = profile or os.environ["WEB_PROFILE"]
        self.output_folder = Path(output_folder) if output_folder else Path.cwd()
        if output_folder:
            self.output_folder.mkdir(parents=True, exist_ok=True)

    def base_options(self) -> _Params:
        return {
            "format": "bestvideo*+bestaudio/best",
            "merge_output_format": "mp4",
            "cookiesfrombrowser": ("firefox", self.profile),  # (browser, profile path)
            "quiet": False,
            "no_warnings": True,
            "ignoreerrors": True,
            "retries": 10,
            "fragment_retries": 10,
            # JS runtime + solver scripts: needed for the "web" client to work.
            # Without them yt-dlp falls back to android_vr, whose streams return 403.
            # Deno (yt-dlp's default runtime) comes from the `yt-dlp[deno]` extra and is found in
            # .venv/Scripts; the solver scripts come from the bundled yt-dlp-ejs package.
            "js_runtimes": {"deno": {}},
            "extractor_retries": 5,
            "sleep_interval_requests": 1,
            "sleep_interval": 5,
            "max_sleep_interval": 15,
        }

    def list_playlist(self, url: str) -> list[_InfoDict]:
        options: _Params = {**self.base_options(), "extract_flat": "in_playlist", "quiet": True}
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:  # with "ignoreerrors", yt-dlp returns None instead of raising
            logger.warning("Could not read playlist %s", url)
            return []

        entries: list[_InfoDict] = [e for e in (info.get("entries") or []) if e]
        logger.info("Playlist '%s': %d video(s).", info.get("title"), len(entries))

        return entries

    def download_playlist(self, url: str):
        entries = self.list_playlist(url)
        total = len(entries)

        options: _Params = {
            **self.base_options(),
            "outtmpl": str(self.output_folder / "%(playlist_index)03d - %(title)s.%(ext)s"),
            "noplaylist": False,
            # skip what's already downloaded
            "download_archive": str(self.output_folder / "downloaded.txt"),
        }

        logger.info("Downloading %d video(s) to %s", total, self.output_folder)
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

    def download_video(self, url: str):
        options: _Params = {**self.base_options(), "outtmpl": str(self.output_folder / "%(title)s.%(ext)s")}
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            logger.info("Downloading %s ...", info.get("title"))
            ydl.download([url])


if __name__ == "__main__":
    output_folder = Path(__file__).parent.parent.parent / "downloads" / "Test"
    youtube = Youtube(output_folder=output_folder)
    youtube.download_video(url="https://www.youtube.com/watch?v=MCYm453CE6Y")
