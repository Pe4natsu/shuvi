import argparse
from pathlib import Path

from shuvi.core.yt import DEFAULT_FILE_FORMAT, FILE_FORMATS, Youtube


def download(url: str, output_folder: Path, file_format: str = DEFAULT_FILE_FORMAT):
    youtube = Youtube(output_folder=output_folder, file_format=file_format)
    youtube.download_video(url)


def run():
    parser = argparse.ArgumentParser(description="Download a YouTube video.")
    parser.add_argument("--url", type=str, help="The URL of the YouTube video.")
    parser.add_argument(
        "--output-folder", type=Path, default=Path.cwd(), help="The folder to save the downloaded video."
    )
    parser.add_argument(
        "--format", choices=list(FILE_FORMATS), default=DEFAULT_FILE_FORMAT, help="The file format to download."
    )
    args = parser.parse_args()

    download(args.url, args.output_folder, args.format)


if __name__ == "__main__":
    run()
