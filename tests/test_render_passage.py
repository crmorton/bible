from bible_api.passage import render_passage_html


def test_render_passage_html_simple():
    # Basic row structure matching the database schema used by the API.
    row = {
        "book": "John",
        "chapter": 3,
        "verse_start": 16,
        "verse_end": 16,
        "h3": None,
        "h2": None,
        "h4": None,
        "h0": None,
        "path": "div.passage->p",
        "class_attr": "",
        "span_text": "For God so loved the world...",
        "span_id": "",
        "para_md5": "abc",
    }
    html = render_passage_html([row], translation="LEB")
    assert "For God so loved" in html
    assert "class=\"verse" in html or "versenum" in html
