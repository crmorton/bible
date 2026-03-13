# Bible Passage API Mock Walkthrough

## What was Accomplished
We took the folder of scraped `HTML`/`.psv` files and created a full end-to-end pipeline to serve Bible passages dynamically via a mock API.
This included:
1. **SQLite Database Schema**: Created a `verses` table in `bible_v2.db` with optimized indexing.
2. **Data Ingestion Script**: `ingest_html.py` now parses raw HTML directly, ensuring high fidelity for structural markers like poetry and headings. **Over 298k unique content spans are now indexed (deduplicated)!**
3. **Advanced Reference Parsing**: Integrated `bcv_parser` (JS) via `py-mini-racer` for robust, standard-compliant reference handling.
4. **Multi-Chapter Support**: Seamlessly reconstructs DOM across chapter boundaries.
5. **Poetry & Formatting Fixes**: Restored and improved the rendering of poetic blocks and indentation.
6. **Dockerization**: Fully containerized with in-memory SQLite loading for sub-millisecond lookups.
7. **Deduplication Mechanism**: Implemented on-the-fly deduplication in `ingest_html.py` to handle overlapping content in source HTML files, ensuring a clean and efficient database.
8. **DOM Path Optimization**: Trimmed redundant high-level container prefixes from the database paths, moving them to a dynamic wrapper in the API. This reduces database size and improves payload efficiency.
9. **Knowledge Items**: Created a dedicated `.agent/knowledge_items` directory containing technical deep-dives into data ingestion, rendering logic, and reference parsing to aid future development.
10. **Git Configuration**: Added a `.gitignore` to protect the repository from large data files and environment artifacts.
11. **Test Frontend**: `index.html` provides a clean UI for verification.

## How to Verify

### Running with Docker (Recommended)
1. Ensure `bible.db` is in the root directory.
2. Run: `docker-compose up --build`
3. Access the UI via `index.html` or explore the API at `http://localhost:8000`.

### Running with Python (Manual)
1. **Install requirements**: `pip install -r requirements.txt`
2. **Run the API**: `python api.py`
3. **Test the UI**: Open `index.html` and search for e.g. `Matthew 4:1-11`.
