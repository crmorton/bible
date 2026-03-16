import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Projects\_dev-workspace\__Antigravity\bible\bible_v2.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Adding translations table to {DB_PATH}...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abbreviation TEXT UNIQUE,
            full_name TEXT,
            publisher_name TEXT,
            publisher_url TEXT,
            about_html TEXT,
            copyright_html TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
