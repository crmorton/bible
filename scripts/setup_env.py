"""Helper to bootstrap the repo for development.

This script will:
1) Download a bible_v2.db file (if not already present)
2) Scrape translations metadata into the database
3) Ingest the scraped HTML into the database

Example:
    python scripts/setup_env.py --db-url https://example.com/bible_v2.db

"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.download_db import download_file
from scripts.ingest_html import ingest_html
from scripts.scrape_translations import scrape_translations


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bootstrap the repo by downloading data and populating the database.")

    parser.add_argument(
        "--db-url",
        help="URL to download the sqlite database file from (e.g. https://.../bible_v2.db).",
    )
    parser.add_argument(
        "--db-path",
        default=Path("bible_v2.db"),
        type=Path,
        help="Local path for the sqlite database file.",
    )
    parser.add_argument(
        "--data-dir",
        default=Path("bible-gateway") / "2026",
        type=Path,
        help="Directory containing scraped HTML to ingest.",
    )
    parser.add_argument(
        "--scrape-limit",
        type=int,
        default=None,
        help="Limit how many translations to scrape (useful for fast dev runs).",
    )

    args = parser.parse_args(argv)

    if args.db_url:
        print(f"Downloading DB from {args.db_url} to {args.db_path}...")
        download_file(args.db_url, str(args.db_path))

    if not args.db_path.exists():
        raise SystemExit(f"Database not found at {args.db_path}. Provide --db-url or create it manually.")

    print("Scraping translations metadata...")
    scrape_translations(db_path=args.db_path, limit=args.scrape_limit)

    print("Ingesting HTML into database...")
    ingest_html(data_dir=args.data_dir, db_path=args.db_path)

    print("✅ Setup complete. You can now run the API with: python -m bible_api.api")


if __name__ == "__main__":
    main()
