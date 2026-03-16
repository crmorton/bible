import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import re

# Paths
BASE_DIR = Path(r"C:\Projects\_dev-workspace\__Antigravity\bible")
DB_PATH = BASE_DIR / "bible_v2.db"

def get_soup(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'lxml')

def scrape_translations(limit=None):
    print("Fetching versions list...")
    soup = get_soup("https://www.biblegateway.com/versions/")
    
    # English translations are usually in rows with class 'en'
    # We use .translation-name to avoid getting audio links (info.php)
    links = soup.select("tr.en .translation-name a")
    print(f"Found {len(links)} English translation links.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for link in links:
        if limit and count >= limit:
            break
            
        href = link['href']
        if "info.php" in href:
            continue
            
        # href like "/versions/Lexham-English-Bible-LEB/" or "/versions/Lexham-English-Bible-LEB/#booklist"
        # We need the full URL
        url = "https://www.biblegateway.com" + href
        
        # Remove fragments and trailing slashes for parsing
        clean_url = href.split('#')[0].strip('/')
        # Extract the ID part from the URL path, e.g., Lexham-English-Bible-LEB
        path_id = clean_url.split('/')[-1]
        
        # Abbreviation is usually the last part of the path-id
        parts = path_id.split('-')
        abbr = parts[-1]
        
        # Special case: some might end in "Bible" (e.g. ASV-Bible)
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
            publisher_url = pub_link['href'] if pub_link and 'href' in pub_link.attrs else ""
            
            # Use REPLACE to handle updates
            cursor.execute('''
                INSERT OR REPLACE INTO translations 
                (abbreviation, full_name, publisher_name, publisher_url, about_html, copyright_html)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (abbr, full_name, publisher_name, publisher_url, about_html, copy_html))
            
            conn.commit()
            count += 1
            print(f"Saved {abbr}")
            
            # Polite delay
            time.sleep(2)
            
        except Exception as e:
            print(f"Error scraping {abbr}: {e}")
            # Continue to next translation
            continue
            
    conn.close()
    print(f"Finished. Scraped {count} translations.")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    scrape_translations(limit)
