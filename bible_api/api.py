"""FastAPI application and routes."""

from pathlib import Path

from fastapi import FastAPI, Query, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import DEFAULT_PORT
from .db import get_db, parse_ref
from .passage import render_passage_html
from .ui import build_api_info_page, build_translations_ui_page, _wrap_html_page

OSIS_BOOKS = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers", "Deut": "Deuteronomy",
    "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth", "1Sam": "1 Samuel", "2Sam": "2 Samuel",
    "1Kgs": "1 Kings", "2Kgs": "2 Kings", "1Chr": "1 Chronicles", "2Chr": "2 Chronicles",
    "Ezra": "Ezra", "Neh": "Nehemiah", "Esth": "Esther", "Job": "Job", "Ps": "Psalms",
    "Prov": "Proverbs", "Eccl": "Ecclesiastes", "Song": "Song of Solomon", "Isa": "Isaiah",
    "Jer": "Jeremiah", "Lam": "Lamentations", "Ezek": "Ezekiel", "Dan": "Daniel",
    "Hos": "Hosea", "Joel": "Joel", "Amos": "Amos", "Obad": "Obadiah", "Jonah": "Jonah",
    "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk", "Zeph": "Zephaniah", "Hag": "Haggai",
    "Zech": "Zechariah", "Mal": "Malachi", "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke",
    "John": "John", "Acts": "Acts", "Rom": "Romans", "1Cor": "1 Corinthians", "2Cor": "2 Corinthians",
    "Gal": "Galatians", "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians",
    "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians", "1Tim": "1 Timothy", "2Tim": "2 Timothy",
    "Titus": "Titus", "Phlm": "Philemon", "Heb": "Hebrews", "Jas": "James", "1Pet": "1 Peter",
    "2Pet": "2 Peter", "1John": "1 John", "2John": "2 John", "3John": "3 John", "Jude": "Jude",
    "Rev": "Revelation"
}


def format_osis_ref(osis_str: str) -> str:
    """Convert OSIS reference (e.g. 'Matt.5.17-Matt.5.18') to human-readable format."""
    if not osis_str:
        return ""

    parts = osis_str.split("-")

    def parse_part(part):
        bits = part.split(".")
        book = OSIS_BOOKS.get(bits[0], bits[0])
        chapter = int(bits[1]) if len(bits) > 1 else None
        verse = int(bits[2]) if len(bits) > 2 else None
        return book, chapter, verse

    try:
        b1, c1, v1 = parse_part(parts[0])
        if len(parts) == 1:
            if c1 is None: return b1
            if v1 is None: return f"{b1} {c1}"
            return f"{b1} {c1}:{v1}"

        b2, c2, v2 = parse_part(parts[1])

        if b1 == b2:
            if c1 == c2:
                if v1 == v2:
                    return f"{b1} {c1}:{v1}"
                return f"{b1} {c1}:{v1}-{v2}"
            return f"{b1} {c1}:{v1}-{c2}:{v2}"
        return f"{b1} {c1}:{v1} - {b2} {c2}:{v2}"
    except Exception:
        return osis_str



def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve static assets (CSS/JS) packaged with the python package.
    # Use a stable path based on the package location so it works no matter the current working directory.
    static_dir = Path(__file__).resolve().parent / "static"
    if not static_dir.exists():
        raise RuntimeError(f"Directory '{static_dir}' does not exist")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=Response)
    def ui_page():
        return Response(content=build_translations_ui_page(), media_type="text/html")

    @app.get("/api-info", response_class=Response)
    def api_info_page():
        return Response(content=build_api_info_page(), media_type="text/html")

    @app.get("/translations")
    def get_translations(response: Response, db=Depends(get_db)):
        response.headers["Cache-Control"] = "public, max-age=86400"
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT translation FROM verses ORDER BY translation;")
        v_rows = cursor.fetchall()
        active_translations = [row[0] for row in v_rows]

        cursor.execute("SELECT * FROM translations ORDER BY abbreviation;")
        t_rows = cursor.fetchall()
        metadata = {row['abbreviation']: dict(row) for row in t_rows}

        result = []
        for abbr in active_translations:
            info = metadata.get(abbr, {"abbreviation": abbr, "full_name": abbr})
            result.append(info)

        return {"translations": result}

    @app.get("/translations/{abbreviation}")
    def get_translation_detail(abbreviation: str, response: Response, db=Depends(get_db)):
        response.headers["Cache-Control"] = "public, max-age=86400"
        cursor = db.cursor()
        cursor.execute("SELECT * FROM translations WHERE abbreviation = ?", (abbreviation,))
        row = cursor.fetchone()
        if not row:
            return {"error": "Translation metadata not found."}
        return dict(row)

    @app.get("/translations-info", response_class=Response)
    def get_translations_info(response: Response, db=Depends(get_db)):
        response.headers["Cache-Control"] = "public, max-age=86400"
        cursor = db.cursor()
        cursor.execute("SELECT abbreviation, full_name, publisher_name FROM translations ORDER BY abbreviation")
        rows = cursor.fetchall()
        items = []
        for row in rows:
            abbr = row["abbreviation"]
            name = row["full_name"] or abbr
            publisher = row["publisher_name"]
            link = f"/translations/{abbr}/info"
            items.append(f"<tr><td><a href=\"{link}\">{abbr}</a></td><td>{name}</td><td>{publisher or ''}</td></tr>")

        body = (
            "<h1>Available Translations</h1>"
            "<p>Click a translation to view additional metadata and usage notes.</p>"
            "<table>"
            "<thead><tr><th>Abbreviation</th><th>Full Name</th><th>Publisher</th></tr></thead>"
            "<tbody>"
            + "".join(items)
            + "</tbody>"
            "</table>"
        )

        return Response(content=_wrap_html_page("Translations", body), media_type="text/html")

    @app.get("/translations/{abbreviation}/info", response_class=Response)
    def get_translation_info_page(abbreviation: str, db=Depends(get_db)):
        cursor = db.cursor()
        cursor.execute("SELECT * FROM translations WHERE abbreviation = ?", (abbreviation,))
        row = cursor.fetchone()
        if not row:
            return Response(content=_wrap_html_page("Translation Not Found", f"<h1>Translation not found</h1><p>No translation metadata found for '{abbreviation}'.</p>"), media_type="text/html")

        data = dict(row)
        title = data.get("full_name") or abbreviation
        about_html = data.get("about_html") or "<p>No additional information available.</p>"
        copyright_html = data.get("copyright_html") or "<p>No copyright information available.</p>"
        publisher = data.get("publisher_name")
        publisher_url = data.get("publisher_url")
        publisher_link = f"<a href=\"{publisher_url}\" target=\"_blank\">{publisher}</a>" if publisher and publisher_url else (publisher or "")

        body = (
            f"<h1>{title}</h1>"
            f"<p><strong>Abbreviation:</strong> {abbreviation}</p>"
            f"<p><strong>Publisher:</strong> {publisher_link}</p>"
            "<h2>About</h2>" + about_html +
            "<h2>Copyright</h2>" + copyright_html +
            "<h2>API Usage</h2>" +
            "<p>Example passage request:</p>" +
            f"<pre><code>GET /passage?ref=John+3:16&translation={abbreviation}</code></pre>"
        )

        return Response(content=_wrap_html_page(title, body), media_type="text/html")

    @app.get("/passage")
    def get_passage(response: Response,
                    ref: str = Query(..., description="Bible passage reference, e.g., 'Matthew 4:1-11'"),
                    translation: str = Query("MSG", description="Translation acronym, e.g., 'MSG'"),
                    psalter: bool = Query(False, description="Use Scottish Psalter for Psalms"),
                    db=Depends(get_db)):
        response.headers["Cache-Control"] = "public, max-age=86400"

        parsed_list = parse_ref(ref)
        if not parsed_list:
            return {"error": "Invalid reference format. Use e.g. 'Matthew 4:1-11'"}

        cursor = db.cursor()
        all_blocks = []

        for parsed in parsed_list:
            c_start, v_start, c_end, v_end = parsed["c_start"], parsed["v_start"], parsed["c_end"], parsed["v_end"]
            book_code = parsed["book"]
            book_name = OSIS_BOOKS.get(book_code, book_code)

            table_name = "verses"
            query_translation = translation
            if psalter and book_name == "Psalms":
                table_name = "psalter_verses"
                query_translation = "ScottishPsalter"

            query = f'''
                SELECT * FROM {table_name} 
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
                "translation": query_translation,
                "book": book_code, # Use the OSIS code for the 'book' column in DB
                "c_start": c_start,
                "c_end": c_end,
                "v_start": v_start,
                "v_end": v_end,
            })

            rows = cursor.fetchall()
            if rows:
                rendered = render_passage_html(rows, query_translation if not psalter else "ScottishPsalter")
                osis = parsed.get("osis", "")
                ref_label = format_osis_ref(osis)
                if ref_label:
                    suffix = " (Scottish Psalter)" if psalter and book_name == "Psalms" else ""
                    rendered += f'<p style="text-align: right; font-style: italic; margin-top: 10px; opacity: 0.8;">— {ref_label}{suffix}</p>'
                all_blocks.append(rendered)


        if not all_blocks:
            return {"html": "<p>No verses found for this reference and translation.</p>"}

        html = "<hr>".join(all_blocks)
        return {"html": html}



    return app


def main():
    import uvicorn
    from .config import DEFAULT_PORT, WEB_CONCURRENCY

    uvicorn.run(
        "bible_api.api:create_app",
        host="0.0.0.0",
        port=DEFAULT_PORT,
        factory=True,
        workers=WEB_CONCURRENCY
    )


if __name__ == "__main__":
    main()
