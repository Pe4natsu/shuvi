import argparse
from pathlib import Path

from shuvi.core.yt import Youtube


def download(url: str, output_folder: Path):
    youtube = Youtube(output_folder=output_folder)
    youtube.download_video(url)


def run():
    parser = argparse.ArgumentParser(description="Download a YouTube video.")
    parser.add_argument("--url", type=str, help="The URL of the YouTube video.")
    parser.add_argument(
        "--output-folder", type=Path, default=Path.cwd(), help="The folder to save the downloaded video."
    )
    args = parser.parse_args()

    download(args.url, args.output_folder)


if __name__ == "__main__":
    run()
