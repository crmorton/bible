import sqlite3
import threading
from pathlib import Path
import re
import os
import json
from functools import lru_cache
from py_mini_racer.py_mini_racer import MiniRacer
from fastapi import FastAPI, Query, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Configuration
DB_PATH = Path(os.getenv("DB_PATH", r"C:\Projects\_dev-workspace\__Antigravity\bible\bible_v2.db"))
LOAD_IN_MEMORY = os.getenv("LOAD_IN_MEMORY", "false").lower() == "true"
SHARED_MEM_URI = "file:/memdb1?vfs=memdb"
thread_local = threading.local()

# Globals
bcv_parser = None # Global bcv parser object
memdb_keepalive = None # Global connection to keep memdb alive in each worker process


def get_db():
    # 2. Each thread gets its own unique connection to the SAME memory space
    if not hasattr(thread_local, "connection"):
        if LOAD_IN_MEMORY:
            # Use immutable=1 and mode=ro for maximum read-only performance
            thread_local.connection = sqlite3.connect(f"{SHARED_MEM_URI}&mode=ro&immutable=1", uri=True, check_same_thread=False)
        else:
            thread_local.connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        thread_local.connection.row_factory = sqlite3.Row
    return thread_local.connection


def init_bcv_parser():
    global bcv_parser
    if bcv_parser is not None:
        return bcv_parser
        
    js_path = Path("en_bcv_parser.js")
    if js_path.exists():
        print(f"Loading {js_path}...")
        with open(js_path, "r", encoding="utf-8") as f:
            js_code = f.read()
            
        bcv_parser = MiniRacer()
        bcv_parser.eval(js_code)
        bcv_parser.eval("bcv = new bcv_parser()")
        bcv_parser.eval('bcv.set_options({ "consecutive_combination_strategy": "separate", "osis_compaction_strategy": "bc", "sequence_combination_strategy": "separate" });')
        print("JS bcv_parser initialized via py-mini-racer.")
        return bcv_parser
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memdb_keepalive
    # Initialize JS bcv_parser
    init_bcv_parser()

    if LOAD_IN_MEMORY and DB_PATH.exists():
        print(f"Loading database {DB_PATH} into memory...")
        # Connect to source and target
        source_conn = sqlite3.connect(DB_PATH)
        # Use a connection to backup into the shared memory space, and keep it open
        memdb_keepalive = sqlite3.connect(SHARED_MEM_URI, uri=True, check_same_thread=False)
        # Backup source to memory
        source_conn.backup(memdb_keepalive)
        source_conn.close()
        print("Database loaded into memory successfully.")
    
    yield
    
    if memdb_keepalive:
        memdb_keepalive.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_private_network_access_header(request, call_next):
    if request.method == "OPTIONS" and request.headers.get("Access-Control-Request-Private-Network"):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response
    response = await call_next(request)
    return response



@lru_cache(maxsize=1024)
def parse_ref_cached(ref_str: str):
    """Internal cached version of parse_ref to minimize JS overhead."""
    parser = init_bcv_parser()
    if not parser:
        return []
    # Escaping single quotes for JS consumption
    safe_ref = ref_str.replace("'", "\\'")
    js_cmd = f"JSON.stringify(bcv.parse('{safe_ref}').parsed_entities().map(entity => ({{ osis: entity.osis, start: entity.start, end: entity.end }})))"
    res_json = parser.eval(js_cmd)
    return json.loads(str(res_json))

def parse_ref(ref_str: str):
    # Fast-path for OSIS references
    if ref_str.startswith("osis:"):
        ref_text = ref_str[5:] # type: ignore
        # Patterns: 
        # Single point: Book.Chap[.Verse]
        # Range: Book.Chap[.Verse]-Book.Chap[.Verse] (Book usually same)
        # We'll split by '-' and parse each part.
        parts = ref_text.split('-')
        
        def parse_osis_part(part):
            # Regex to match Book.Chapter.Verse or Book.Chapter
            match = re.match(r'^([1-3]?[A-Za-z]+)\.(\d+)(?:\.(\d+))?$', part)
            if not match:
                return None
            book = match.group(1)
            chapter = int(match.group(2))
            verse = int(match.group(3)) if match.group(3) else None
            return {"b": book, "c": chapter, "v": verse}

        start_entity = parse_osis_part(parts[0])
        if not start_entity:
            return None
            
        if len(parts) > 1:
            end_entity = parse_osis_part(parts[1])
            if not end_entity:
                return None
        else:
            end_entity = start_entity.copy()

        # If verse is missing in an OSIS part, we treat it as the whole chapter
        # We need to set v_start=1 and v_end to something large if it's a chapter-level ref
        # but the JS parser usually returns v=1 for start of chapter and v=999(ish) for end?
        # Let's check how the DB query handles it. 
        # v_start and v_end in DB are integers.
        # If user says Ps.121, they mean the whole chapter 121.
        
        return {
            "book": start_entity["b"],
            "c_start": start_entity["c"],
            "v_start": start_entity["v"] if start_entity["v"] is not None else 1,
            "c_end": end_entity["c"],
            "v_end": end_entity["v"] if end_entity["v"] is not None else 999 
        }

    # Use the JS parser
    try:
        entities = parse_ref_cached(ref_str)
        
        if not entities:
            return None
            
        entity = entities[0]
        book = entity['start']['b']
        c_start = entity['start']['c']
        v_start = entity['start']['v']
        c_end = entity['end']['c']
        v_end = entity['end']['v']
        
        return {
            "book": book,
            "c_start": c_start,
            "v_start": v_start,
            "c_end": c_end,
            "v_end": v_end
        }
    except Exception as e:
        print(f"Parsing error: {e}")
        return None

@app.get("/translations")
def get_translations(response: Response, db: sqlite3.Connection = Depends(get_db)):
    # Cache translations for 24 hours at the Edge
    response.headers["Cache-Control"] = "public, max-age=86400"
    cursor = db.cursor()
    
    # Get all distinct translations from verses
    cursor.execute("SELECT DISTINCT translation FROM verses ORDER BY translation;")
    v_rows = cursor.fetchall()
    active_translations = [row[0] for row in v_rows]
    
    # Get metadata from translations table
    cursor.execute("SELECT * FROM translations ORDER BY abbreviation;")
    t_rows = cursor.fetchall()
    metadata = {row['abbreviation']: dict(row) for row in t_rows}
    
    result = []
    for abbr in active_translations:
        info = metadata.get(abbr, {"abbreviation": abbr, "full_name": abbr})
        result.append(info)
        
    return {"translations": result}

@app.get("/translations/{abbreviation}")
def get_translation_detail(abbreviation: str, response: Response, db: sqlite3.Connection = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=86400"
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM translations WHERE abbreviation = ?", (abbreviation,))
    row = cursor.fetchone()
    
    if not row:
        return {"error": "Translation metadata not found."}
        
    return dict(row)

def parse_tag(tag_str):
    # tag_str like "div.poetry" or "p"
    parts = tag_str.split('.')
    tag_name = parts[0]
    classes = " ".join(parts[1:])
    class_attr = f' class="{classes}"' if classes else ''
    return f"<{tag_name}{class_attr}>", f"</{tag_name}>"

@app.get("/passage")
def get_passage(response: Response,
                ref: str = Query(..., description="Bible passage reference, e.g., 'Matthew 4:1-11'"),
                translation: str = Query("MSG", description="Translation acronym, e.g., 'MSG'"),
                db: sqlite3.Connection = Depends(get_db)):
    # Cache passage for 24 hours at the Edge (Cloudflare)
    response.headers["Cache-Control"] = "public, max-age=86400"
    
    parsed = parse_ref(ref)
    if not parsed: return {"error": "Invalid reference format. Use e.g. 'Matthew 4:1-11'"}
    
    book = parsed["book"]
    c_start, v_start = parsed["c_start"], parsed["v_start"]
    c_end, v_end = parsed["c_end"], parsed["v_end"]
    
    cursor = db.cursor()
    
    # Optimized range query
    # Branches:
    # 1. Start and end are in the same chapter
    # 2. Multi-chapter range: Start chapter
    # 3. Multi-chapter range: End chapter
    # 4. Multi-chapter range: Intermediate chapters
    query = '''
        SELECT * FROM verses 
        WHERE translation = :translation 
          AND book = :book 
          AND (
            (chapter = :c_start AND chapter = :c_end AND verse_start <= :v_end AND verse_end >= :v_start)
            OR
            (chapter = :c_start AND :c_start < :c_end AND verse_end >= :v_start)
            OR
            (chapter = :c_end AND :c_start < :c_end AND verse_start <= :v_end)
            OR
            (chapter > :c_start AND chapter < :c_end)
          )
        ORDER BY chapter, verse_start ASC
    '''
    cursor.execute(query, {
        "translation": translation, 
        "book": book, 
        "c_start": c_start, 
        "c_end": c_end, 
        "v_start": v_start, 
        "v_end": v_end
    })
    
    rows = cursor.fetchall()
    
    if not rows:
        return {"html": "<p>No verses found for this reference and translation.</p>"}

    # Reconstruct HTML Tree
    res_html = []
    # current_path_tags will store tuples of (tag_id_string, close_tag)
    # tag_id_string is like "div.poetry" or "span.indent-1"
    current_path_tags = []
    current_para_md5 = None
    
    rendered_chapter = None
    rendered_verse = None
    is_first_span_in_para = True
    
    for row in rows:
        book_db = row['book']
        chapter_db = row['chapter']
        v_start_db = row['verse_start']
        v_end_db = row['verse_end']
        h3, h2, h4, h0 = row['h3'], row['h2'], row['h4'], row['h0']
        header_text = h3 or h2 or h4 or h0
        
        if header_text:
            # If there's a heading, we likely need to close any open paragraphs before it
            while current_path_tags:
                res_html.append(current_path_tags.pop()[1])
            current_para_md5 = None
            
        path = row['path']
        class_attr = row['class_attr']
        span_text = row['span_text'] or header_text
        span_id = row['span_id'] or ""
        para_md5 = row['para_md5']
        
        target_tags = path.split('->') if path else []
        
        # If the paragraph changes based on para_md5, close everything
        if para_md5 != current_para_md5:
            while current_path_tags:
                res_html.append(current_path_tags.pop()[1])
            current_para_md5 = para_md5
            is_first_span_in_para = True
            
        # If continuing a paragraph in a poetry block, insert <br> before adjusting tags for the new line
        if "poetry" in path and not is_first_span_in_para:
            res_html.append("<br>")
            
        # Adjust tags to match the current path
        # 1. Find common prefix
        common_count = 0
        for i in range(min(len(current_path_tags), len(target_tags))):
            if current_path_tags[i][0] == target_tags[i]:
                common_count += 1
            else:
                break
        
        # 2. Close tags that differ
        while len(current_path_tags) > common_count:
            res_html.append(current_path_tags.pop()[1])
            
        # 3. Open missing tags
        for i in range(common_count, len(target_tags)):
            tag_str = target_tags[i]
            open_tag, close_tag = parse_tag(tag_str)
            
            # Inject spacing around paragraphs and poetry blocks
            if "poetry" in open_tag:
                open_tag = open_tag.replace('>', ' style="margin-top: 15px; margin-bottom: 15px;">')
            elif open_tag.startswith("<p"):
                # Handle consecutive paragraphs
                open_tag = open_tag.replace('>', ' style="margin-bottom: 10px;">')
            elif any(h in open_tag for h in ["<h1","<h2","<h3","<h4"]):
                open_tag = open_tag.replace('>', ' style="margin-top: 20px; margin-bottom: 10px;">')
            
            res_html.append(open_tag)
            current_path_tags.append((tag_str, close_tag))
            
            # Inject indent breaks if this is an indentation span
            if "span.indent-" in tag_str:
                level_match = re.search(r'indent-(\d+)', tag_str)
                if level_match:
                    level = int(level_match.group(1))
                    # Bible Gateway uses 4 non-breaking spaces per indent level
                    spaces = " " * (level * 4) 
                    res_html.append(f'<span class="indent-{level}-breaks">{spaces}</span>')
                
        span_id_attr = f' id="{span_id}"' if span_id else ""
        
        # Inject Chapter / Verse numbers
        prefix = ""
        # Don't inject verse numbers into headers
        is_header = bool(header_text) or any(h in path for h in ['h1', 'h2', 'h3', 'h4'])
        
        # Check if we moved to a new verse/chapter
        if not is_header and (chapter_db != rendered_chapter or v_start_db != rendered_verse):
            rendered_chapter = chapter_db
            rendered_verse = v_start_db
            verse_label = str(v_start_db) if v_start_db == v_end_db else f"{v_start_db}-{v_end_db}"
            
            if v_start_db == 1:
                prefix = f'<span class="chapternum" style="float: left; padding-right: 6px;">{chapter_db}</span>'
            else:
                prefix = f'<sup class="versenum">{verse_label} </sup>'
                
        span_html = f"<span{span_id_attr} class=\"{class_attr}\">{prefix}{span_text}</span>"
        res_html.append(span_html)
        
        is_first_span_in_para = False
        
    # Close any remaining tags
    while current_path_tags:
        res_html.append(current_path_tags.pop()[1])

    inner_html = "".join(res_html)
    # Wrap in redundant containers for CSS compatibility
    wrapped_html = (
        f'<div class="passage-text">'
        f'<div class="passage-content passage-class-0">'
        f'<div class="version-{translation} result-text-style-normal text-html">'
        f'{inner_html}'
        f'</div></div></div>'
    )

    return {"html": wrapped_html}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # Note: Multi-worker uvicorn is unstable on Windows via python script.
    # 1 worker + async handling is plenty for an in-memory SQLite DB.
    uvicorn.run("api:app", host="0.0.0.0", port=port, workers=5)
