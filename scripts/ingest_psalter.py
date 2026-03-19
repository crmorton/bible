"""Ingest Scottish Psalter PSV files into the SQLite database."""

import csv
import sqlite3
import re
from pathlib import Path

def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def setup_psalter_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()
    
    # Metadata table
    cursor.execute("DROP TABLE IF EXISTS psalter")
    cursor.execute("""
        CREATE TABLE psalter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            psalter_name TEXT,
            psalter_book TEXT,
            psalm INTEGER,
            subtitle TEXT,
            version TEXT,
            meter TEXT
        )
    """)
    
    # Verses table
    cursor.execute("DROP TABLE IF EXISTS psalter_verses")
    cursor.execute("""
        CREATE TABLE psalter_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT,
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,
            verse_end INTEGER,
            para_md5 INTEGER,
            path TEXT,
            class_attr TEXT,
            span_id TEXT,
            h0 TEXT,
            h2 TEXT,
            h3 TEXT,
            h4 TEXT,
            span_text TEXT,
            psalter_name TEXT,
            psalter_book TEXT,
            version TEXT,
            meter TEXT,
            canto TEXT,
            canto_id INTEGER,
            stanza_quartrain INTEGER,
            line_indent TEXT,
            line_num INTEGER
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_psalter_lookup ON psalter_verses(chapter, verse_start)")
    conn.commit()

def ingest_psalter(db_path: Path, psalter_psv: Path, verses_psv: Path):
    conn = sqlite3.connect(db_path)
    setup_psalter_tables(conn)
    cursor = conn.cursor()
    
    # Ingest Metadata
    print(f"Ingesting metadata from {psalter_psv}...")
    psalter_metadata = {} # Map (Psalm, Version) -> Subtitle
    with open(psalter_psv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO psalter (psalter_name, psalter_book, psalm, subtitle, version, meter)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row['Psalter'], row['Psalter Book'], int(row['Psalm']), 
                row['Subtitle'], row['Version'], row['Meter']
            ))
            psalter_metadata[(int(row['Psalm']), row['Version'])] = row['Subtitle']
    
    # Ingest Verses
    print(f"Ingesting verses from {verses_psv}...")
    with open(verses_psv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows_to_insert = []
        
        last_canto_id = None
        last_psalm = None
        last_version = None
        
        for row in reader:
            psalm = int(row['Psalm'])
            version = row['Version']
            canto_id = int(row['CantoID'])
            stanza = int(row['StanzaQuartrain'])
            v_num = int(row['VerseNum'])
            
            # Determine headers
            h3 = None
            if psalm != last_psalm or version != last_version:
                h3 = psalter_metadata.get((psalm, version))
            
            h4 = None
            if canto_id != last_canto_id:
                h4 = row['Canto']
                
            # Path and indent
            path = "div.poetry->p.line"
            if v_num == 1:
                path += "->span.chapter-1"
            if row['LineIndent'] == 'Y':
                path += "->span.indent-1"
                
            # para_md5 based on StanzaQuartrain and CantoID to ensure breaks
            para_md5 = (canto_id * 1000) + stanza
            
            rows_to_insert.append((
                "ScottishPsalter", # Internal translation name
                "Ps",
                psalm,
                v_num,
                v_num,
                para_md5,
                path,
                f"text Ps-{psalm}-{v_num}",
                None, # span_id
                None, # h0
                None, # h2
                h3,
                h4,
                row['SpanText'],
                row['Psalter'],
                row['Psalter Book'],
                version,
                row['Meter'],
                row['Canto'],
                canto_id,
                stanza,
                row['LineIndent'],
                int(row['LineNum'])
            ))
            
            last_canto_id = canto_id
            last_psalm = psalm
            last_version = version
            
        cursor.executemany("""
            INSERT INTO psalter_verses (
                translation, book, chapter, verse_start, verse_end,
                para_md5, path, class_attr, span_id, h0, h2, h3, h4, span_text,
                psalter_name, psalter_book, version, meter,
                canto, canto_id, stanza_quartrain, line_indent, line_num
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)

        
    conn.commit()
    conn.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    root = get_repo_root()
    db = root / "bible_v2.db"
    psalter = root / "extra" / "psalter.psv"
    verses = root / "extra" / "psalter_verses.psv"
    
    ingest_psalter(db, psalter, verses)
