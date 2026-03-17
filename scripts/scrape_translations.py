"""Scrape Bible translation metadata into the local SQLite database.

This script is intended to be run from the repository root.

Example:
    python scripts/scrape_translations.py --db-path ./bible_v2.db --limit 20

"""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def get_repo_root() -> Path:
    # scripts/ is inside the repo root; this returns the repo root path.
    return Path(__file__).resolve().parents[1]


def get_default_db_path() -> Path:
    return get_repo_root() / "bible_v2.db"


def get_soup(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def scrape_translations(db_path: Path, limit: int | None = None):
    print("Fetching versions list...")
    soup = get_soup("https://www.biblegateway.com/versions/")

    links = soup.select("tr.en .translation-name a")
    print(f"Found {len(links)} English translation links.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count = 0
    for link in links:
        if limit and count >= limit:
            break

        href = link["href"]
        if "info.php" in href:
            continue

        url = "https://www.biblegateway.com" + href
        clean_url = href.split("#")[0].strip("/")
        path_id = clean_url.split("/")[-1]

        parts = path_id.split("-")
        abbr = parts[-1]
        if abbr.lower() == "bible" and len(parts) > 1:
            abbr = parts[-2]

        full_name = link.get_text(strip=True)

        try:
            print(f"Scraping {abbr}: {full_name} ({url})...")
            v_soup = get_soup(url)

            about_div = v_soup.select_one(".vinfo-content")
            about_html = str(about_div) if about_div else ""

            copy_div = v_soup.select_one(".copy-content")
            copy_html = str(copy_div) if copy_div else ""

            pub_link = v_soup.select_one(".publisher-link a")
            publisher_name = pub_link.get_text(strip=True) if pub_link else ""
            publisher_url = pub_link["href"] if pub_link and "href" in pub_link.attrs else ""

            cursor.execute(
                """
                INSERT OR REPLACE INTO translations
                (abbreviation, full_name, publisher_name, publisher_url, about_html, copyright_html)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (abbr, full_name, publisher_name, publisher_url, about_html, copy_html),
            )
            conn.commit()
            count += 1
            print(f"Saved {abbr}")

            time.sleep(2)

        except Exception as e:
            print(f"Error scraping {abbr}: {e}")
            continue

    conn.close()
    print(f"Finished. Scraped {count} translations.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scrape Bible translation metadata into the SQLite database.")
    parser.add_argument(
        "--db-path",
        default=get_default_db_path(),
        type=Path,
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of translations to scrape",
    )

    args = parser.parse_args(argv)

    scrape_translations(db_path=args.db_path, limit=args.limit)


if __name__ == "__main__":
    main()
