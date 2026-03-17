"""FastAPI application and routes."""

from fastapi import FastAPI, Query, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import DEFAULT_PORT
from .db import get_db, parse_ref
from .passage import render_passage_html
from .ui import build_api_info_page, build_translations_ui_page, _wrap_html_page


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve scraped static assets (CSS/HTML) so the UI matches the old index page.
    app.mount("/bible-gateway", StaticFiles(directory="bible-gateway"), name="bible-gateway")

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
                    db=Depends(get_db)):
        response.headers["Cache-Control"] = "public, max-age=86400"

        parsed = parse_ref(ref)
        if not parsed:
            return {"error": "Invalid reference format. Use e.g. 'Matthew 4:1-11'"}

        cursor = db.cursor()
        c_start, v_start, c_end, v_end = parsed["c_start"], parsed["v_start"], parsed["c_end"], parsed["v_end"]

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
            "book": parsed["book"],
            "c_start": c_start,
            "c_end": c_end,
            "v_start": v_start,
            "v_end": v_end,
        })

        rows = cursor.fetchall()
        if not rows:
            return {"html": "<p>No verses found for this reference and translation.</p>"}

        html = render_passage_html(rows, translation)
        return {"html": html}

    return app


def main():
    import uvicorn
    from .config import DEFAULT_PORT

    uvicorn.run("bible_api.api:create_app()", host="0.0.0.0", port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
