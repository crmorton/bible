"""Download a Bible SQLite DB file for use with the API.

This helper is intentionally lightweight and does not enforce any particular
hosting arrangement. It is meant to be used by developers/operators who have a
URL to a pre-built `bible_v2.db` file (or similar).

Examples:
    python scripts/download_db.py \
        --url https://example.com/bible_v2.db \
        --output bible_v2.db

    # Use environment variable if available:
    export BIBLE_DB_URL=https://example.com/bible_v2.db
    python scripts/download_db.py

"""

from __future__ import annotations

import argparse
import os
import sys

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def download_file(url: str, destination: str, chunk_size: int = 32_768):
    if requests is None:
        raise RuntimeError("The 'requests' package is required. Install with: pip install requests")

    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    print(f"Downloading {url} to {destination} ({total or '?'} bytes)...")

    with open(destination, "wb") as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r{downloaded}/{total} bytes ({pct:.1f}%)", end="")

    if total:
        print("\rDownload complete.            ")
    else:
        print("Download complete.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download a Bible SQLite database file for use with the API.")
    parser.add_argument(
        "--url",
        help="URL pointing to the SQLite DB file (e.g. https://example.com/bible_v2.db).",
        default=os.environ.get("BIBLE_DB_URL"),
    )
    parser.add_argument(
        "--output",
        help="Local output path for the downloaded file.",
        default="bible_v2.db",
    )

    args = parser.parse_args(argv)

    if not args.url:
        parser.error("A URL must be provided via --url or BIBLE_DB_URL environment variable.")

    if os.path.exists(args.output):
        print(f"Warning: Overwriting existing file: {args.output}")

    download_file(args.url, args.output)


if __name__ == "__main__":
    main()
