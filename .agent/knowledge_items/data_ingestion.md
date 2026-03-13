# Bible Data Ingestion Pipeline

## Overview
The ingestion pipeline transforms raw HTML scrapes from Bible Gateway into a highly optimized SQLite database (`bible_v2.db`).

## Core Logic (`ingest_html.py`)
- **Direct HTML Parsing**: Uses `BeautifulSoup` and `lxml` to traverse the DOM of the source HTML files.
- **Content Spans**: Instead of storing whole verses, the script extracts "content spans" which are the smallest units of text within a specific DOM path.
- **Path Reconstruction**: Every span is stored with its relative DOM path (e.g., `div.poetry->p.line`). Redundant high-level containers are trimmed during ingestion to save space.
- **On-the-fly Deduplication**: Tracks a "signature" of every span `(translation, book, chapter, v_start, v_end, span_id, span_text, path)` to prevent duplicate records when source files overlap.
- **Metadata Capture**: 
    - `para_md5`: A unique identifier for the parent container, used by the API to determine when to close/open tags.
    - `Headings`: Captures `h1-h4` tags and associates them with the following verses.

## Production Deployment Strategy
To ensure ultra-fast startup and portability, the deployment process uses a **Baked-In Database** strategy:
- **Stateless Infrastructure**: The `bible_v2.db` is included in the production Docker image.
- **Instant Scaling**: Since the data is included in the image, Cloud Run can scale out globally without depending on a centralized database or network storage, maintaining high performance across all regions.
