import os
import sqlite3
import csv
import re
from pathlib import Path

# Paths
BASE_DIR = Path(r"C:\Projects\_dev-workspace\__Antigravity\bible")
DATA_DIR = BASE_DIR / "bible-gateway" / "2026"
DB_PATH = BASE_DIR / "bible_2026.db"

# Setup DB
def setup_db(conn):
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS verses')
    cursor.execute('''
        CREATE TABLE verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT,
            book TEXT,
            chapter INTEGER,
            verse_start INTEGER,
            verse_end INTEGER,
            bg_id INTEGER,
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
    ''')
    # Indexes to speed up queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_verses_lookup ON verses(translation, book, chapter);')
    conn.commit()


def parse_class_attr(class_attr):
    # e.g., "text Matt-1-2"
    # e.g., "text Matt-1-2-Matt-1-11"
    # e.g., "text Matt-4-1"
    match = re.search(r'text\s+([A-Za-z0-9]+)-(\d+)-(\d+)(?:-([A-Za-z0-9]+)-(\d+)-(\d+))?', str(class_attr))
    
    book = None
    chapter = None
    verse_start = None
    verse_end = None

    if match:
        book = match.group(1)
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        
        # If it's a range
        if match.group(6):
            verse_end = int(match.group(6))
        else:
            verse_end = verse_start
            
    return book, chapter, verse_start, verse_end

def ingest_data():
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    cursor = conn.cursor()

    count = 0
    duplicates = 0
    seen = set()
    
    # Find all PSV files
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".psv"):
                filepath = os.path.join(root, file)
                print(f"Ingesting: {file}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=',')
                    
                    rows_to_insert = []
                    for row in reader:
                        translation = row.get('vsn', '')
                        bg_id_str = row.get('bg_id', '')
                        bg_id = int(bg_id_str) if bg_id_str else None
                        span_id = row.get('span_id', '')
                        class_attr = row.get('class_attr', '')
                        para_md5_str = row.get('para_md5', '')
                        
                        # para_md5 is a hash string we convert to int, or we just cast if it's already an integer string.
                        # Assuming para_md5 in the file is a numerical string based on user's request
                        para_md5 = int(para_md5_str) if para_md5_str and para_md5_str.isdigit() else (int(para_md5_str, 16) if para_md5_str else None)
                        
                        path = row.get('path', '')
                        span_type = row.get('span_type', '')
                        span_indent = row.get('span_indent', '')
                        span_text = row.get('span_text', '')
                        h0 = row.get('h0', '')
                        h2 = row.get('h2', '')
                        h3 = row.get('h3', '')
                        h4 = row.get('h4', '')
                        
                        book, chapter, verse_start, verse_end = parse_class_attr(class_attr)
                        
                        # Create a unique key for deduplication
                        # We use translation, book, chapter, verse and the actual content/paths
                        key = (translation, book, chapter, verse_start, verse_end, bg_id, span_id, path, h3, h2, h4, span_text)
                        if key in seen:
                            duplicates += 1
                            continue
                        seen.add(key)

                        rows_to_insert.append((
                            translation, book, chapter, verse_start, verse_end,
                            bg_id, span_id, class_attr, para_md5, path, 
                            span_type, span_indent, h0, h2, h3, h4, span_text
                        ))
                    
                    cursor.executemany('''
                        INSERT INTO verses (
                            translation, book, chapter, verse_start, verse_end,
                            bg_id, span_id, class_attr, para_md5, path,
                            span_type, span_indent, h0, h2, h3, h4, span_text
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', rows_to_insert)
                    conn.commit()
                    count += len(rows_to_insert)
    
    conn.close()
    print(f"Successfully ingested {count} records.")
    print(f"Skipped {duplicates} duplicate records due to file overlap.")

if __name__ == "__main__":
    ingest_data()
