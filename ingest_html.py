import os
import sqlite3
import re
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

# Paths
BASE_DIR = Path(r"C:\Projects\_dev-workspace\__Antigravity\bible")
DATA_DIR = BASE_DIR / "bible-gateway" / "2026"
DB_PATH = BASE_DIR / "bible_v2.db"

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
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_verses_lookup ON verses(translation, book, chapter);')
    conn.commit()

def get_path(element):
    """Reconstructs the DOM path like div.poetry->p.line->span.text"""
    tags = []
    curr = element.parent # Start from parent since the element itself is the span
    while curr and curr.name not in [None, '[document]', 'body']:
        # Stop at the version-specific div to trim redundant prefixes
        classes = curr.get('class', [])
        if any(cls.startswith('version-') for cls in classes):
            break
            
        name = curr.name
        classes = ".".join(curr.get('class', []))
        # Filter out very long classes or ad-hoc ones if needed, 
        # but for structural tags we want them.
        tag_str = f"{name}.{classes}" if classes else name
        tags.append(tag_str)
        curr = curr.parent
    
    return "->".join(reversed(tags))

def parse_class_attr(class_attr):
    # e.g., "text Matt-1-2"
    # e.g., "text Matt-1-2-Matt-1-11"
    match = re.search(r'text\s+([A-Za-z0-9]+)-(\d+)-(\d+)(?:-([A-Za-z0-9]+)-(\d+)-(\d+))?', str(class_attr))
    
    if match:
        book = match.group(1)
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(6)) if match.group(6) else verse_start
        return book, chapter, verse_start, verse_end
    return None, None, None, None

def ingest_html():
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    cursor = conn.cursor()

    total_count = 0
    # Map of (translation, book, chapter, verse_start, verse_end, span_id, span_text, path) -> True
    processed_spans = set()
    
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".html"):
                filepath = Path(root) / file
                print(f"Processing: {file}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'lxml')
                
                # Each translation is in a passage-col
                cols = soup.find_all('div', class_='passage-col')
                for col in cols:
                    translation = col.get('data-translation')
                    if not translation:
                        continue
                    
                    rows_to_insert = []
                    
                    # Find all spans that represent text or headings
                    # We can iterate through the passage-text div
                    passage_text = col.find('div', class_='passage-text')
                    if not passage_text:
                        continue
                        
                    # We need to track the current "paragraph" for para_md5
                    # In the original data, para_md5 seems to group elements in the same <p> or <div> block
                    
                    # Also headings can exist
                    current_headings = {"h0": None, "h2": None, "h3": None, "h4": None}
                    
                    # Let's iterate through all descendants of passage_text that contain text
                    for element in passage_text.find_all(recursive=True):
                        # Avoid double-counting nested elements: we only care about the spans with 'text' class
                        # or heading tags
                        
                        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                            # Update current headings
                            h_tag = 'h0' if element.name == 'h1' else element.name
                            if h_tag in current_headings:
                                # Clear lower level headings? Maybe not.
                                current_headings[h_tag] = element.get_text(strip=True)
                            continue

                        if element.name == 'span' and 'text' in element.get('class', []):
                            class_attr = " ".join(element.get('class', []))
                            book, chapter, v_start, v_end = parse_class_attr(class_attr)
                            
                            if not book:
                                continue
                                
                            span_id = element.get('id', '')
                            # bg_id in the original data was numerical. In HTML it might be in the ID or just a hash.
                            # For matthew 1-1 it was 23145.
                            # en-LEB-23145
                            bg_id_match = re.search(r'-(\d+)$', span_id)
                            bg_id = bg_id_match.group(1) if bg_id_match else None
                            
                            # Reconstruct path
                            path = get_path(element)
                            
                            # text content
                            span_text = ""
                            for content in element.children:
                                if isinstance(content, NavigableString):
                                    span_text += str(content)
                                elif content.name not in ['sup', 'span'] or 'versenum' not in content.get('class', []):
                                    # If it's a trans-change or similar, keep text
                                    span_text += content.get_text()
                                    
                            span_text = span_text.strip()
                            if not span_text:
                                continue
                            
                            # Deduplication check
                            span_signature = (translation, book, chapter, v_start, v_end, span_id, span_text, path)
                            if span_signature in processed_spans:
                                continue
                            processed_spans.add(span_signature)
                                
                            # para_md5
                            parent_p = element.find_parent(['p', 'div', 'h1', 'h2', 'h3', 'h4'])
                            para_id = id(parent_p) if parent_p else 0
                            para_md5 = para_id # We can just use an int
                            
                            rows_to_insert.append((
                                translation, book, chapter, v_start, v_end,
                                bg_id, span_id, class_attr, para_md5, path,
                                "N", # span_type (N for Normal usually)
                                "",  # span_indent
                                current_headings['h0'], current_headings['h2'], 
                                current_headings['h3'], current_headings['h4'],
                                span_text
                            ))
                            
                            # Clear headings once used
                            for k in current_headings:
                                current_headings[k] = None

                    if rows_to_insert:
                        cursor.executemany('''
                            INSERT INTO verses (
                                translation, book, chapter, verse_start, verse_end,
                                bg_id, span_id, class_attr, para_md5, path,
                                span_type, span_indent, h0, h2, h3, h4, span_text
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', rows_to_insert)
                        conn.commit()
                        total_count += len(rows_to_insert)

    conn.close()
    print(f"Finished. Total records inserted: {total_count}")

if __name__ == "__main__":
    ingest_html()
