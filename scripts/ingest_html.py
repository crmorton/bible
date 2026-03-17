"""Ingest HTML files from `bible-gateway/` into the SQLite database.

This script is intended to be run from the repository root.

Example:
    python scripts/ingest_html.py --data-dir ./bible-gateway/2026 --db-path ./bible_v2.db

"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString


def get_repo_root() -> Path:
    # scripts/ is inside the repo root; this returns the repo root path.
    return Path(__file__).resolve().parents[1]


def get_default_paths():
    root = get_repo_root()
    return {
        "db_path": root / "bible_v2.db",
        "data_dir": root / "bible-gateway" / "2026",
    }


def setup_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS verses")
    cursor.execute(
        """
        CREATE TABLE verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT,
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,
            verse_end INTEGER,
            bg_id TEXT,
            span_id TEXT,
            class_attr TEXT,
            para_md5 INTEGER,
            path TEXT,
            span_type TEXT,
            span_indent TEXT,
            h0 TEXT,
            h2 TEXT,
            h3 TEXT,
            h4 TEXT,
            span_text TEXT
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_verses_lookup ON verses(translation, book, chapter);"
    )
    conn.commit()


def get_path(element):
    """Reconstructs the DOM path like div.poetry->p.line->span.text."""
    tags = []
    curr = element.parent  # Start from parent since the element itself is the span
    while curr and curr.name not in [None, "[document]", "body"]:
        # Stop at the version-specific div to trim redundant prefixes
        classes = curr.get("class", [])
        if any(cls.startswith("version-") for cls in classes):
            break

        name = curr.name
        classes = ".".join(curr.get("class", []))
        tag_str = f"{name}.{classes}" if classes else name
        tags.append(tag_str)
        curr = curr.parent

    return "->".join(reversed(tags))


def parse_class_attr(class_attr: str):
    match = re.search(
        r"text\s+([A-Za-z0-9]+)-(\d+)-(\d+)(?:-([A-Za-z0-9]+)-(\d+)-(\d+))?",
        str(class_attr),
    )

    if match:
        book = match.group(1)
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(6)) if match.group(6) else verse_start
        return book, chapter, verse_start, verse_end
    return None, None, None, None


def ingest_html(data_dir: Path, db_path: Path):
    conn = sqlite3.connect(db_path)
    setup_db(conn)
    cursor = conn.cursor()

    total_count = 0
    processed_spans = set()

    for root, _, files in os.walk(data_dir):
        for file in files:
            if not file.endswith(".html"):
                continue

            filepath = Path(root) / file
            print(f"Processing: {filepath}")

            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "lxml")

            cols = soup.find_all("div", class_="passage-col")
            for col in cols:
                translation = col.get("data-translation")
                if not translation:
                    continue

                rows_to_insert = []
                passage_text = col.find("div", class_="passage-text")
                if not passage_text:
                    continue

                current_headings = {"h0": None, "h2": None, "h3": None, "h4": None}

                for element in passage_text.find_all(recursive=True):
                    if element.name in ["h1", "h2", "h3", "h4", "h5"]:
                        h_tag = "h0" if element.name == "h1" else element.name
                        if h_tag in current_headings:
                            current_headings[h_tag] = element.get_text(strip=True)
                        continue

                    if element.name == "span" and "text" in element.get("class", []):
                        class_attr = " ".join(element.get("class", []))
                        book, chapter, v_start, v_end = parse_class_attr(class_attr)
                        if not book:
                            continue

                        span_id = element.get("id", "")
                        bg_id_match = re.search(r"-(\d+)$", span_id)
                        bg_id = bg_id_match.group(1) if bg_id_match else None

                        path = get_path(element)

                        span_text = ""
                        for content in element.children:
                            if isinstance(content, NavigableString):
                                span_text += str(content)
                            elif content.name not in ["sup", "span"] or "versenum" not in content.get("class", []):
                                span_text += content.get_text()

                        span_text = span_text.strip()
                        if not span_text:
                            continue

                        span_signature = (
                            translation,
                            book,
                            chapter,
                            v_start,
                            v_end,
                            span_id,
                            span_text,
                            path,
                        )
                        if span_signature in processed_spans:
                            continue
                        processed_spans.add(span_signature)

                        parent_p = element.find_parent(["p", "div", "h1", "h2", "h3", "h4"])
                        para_id = id(parent_p) if parent_p else 0
                        para_md5 = para_id

                        rows_to_insert.append(
                            (
                                translation,
                                book,
                                chapter,
                                v_start,
                                v_end,
                                bg_id,
                                span_id,
                                class_attr,
                                para_md5,
                                path,
                                "N",
                                "",
                                current_headings["h0"],
                                current_headings["h2"],
                                current_headings["h3"],
                                current_headings["h4"],
                                span_text,
                            )
                        )

                        for k in current_headings:
                            current_headings[k] = None

                if rows_to_insert:
                    cursor.executemany(
                        """
                        INSERT INTO verses (
                            translation, book, chapter, verse_start, verse_end,
                            bg_id, span_id, class_attr, para_md5, path,
                            span_type, span_indent, h0, h2, h3, h4, span_text
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows_to_insert,
                    )
                    conn.commit()
                    total_count += len(rows_to_insert)

    conn.close()
    print(f"Finished. Total records inserted: {total_count}")


def main(argv=None):
    defaults = get_default_paths()

    parser = argparse.ArgumentParser(description="Ingest scraped Bible HTML into an SQLite database.")
    parser.add_argument("--data-dir", default=defaults["data_dir"], type=Path, help="Path to the scraped bible-gateway HTML folder")
    parser.add_argument("--db-path", default=defaults["db_path"], type=Path, help="Path to the SQLite database file")

    args = parser.parse_args(argv)

    ingest_html(args.data_dir, args.db_path)


if __name__ == "__main__":
    main()
