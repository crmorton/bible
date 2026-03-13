# Bible Passage API Mock Walkthrough

## What was Accomplished
We took the folder of scraped `HTML`/`.psv` files and created a full end-to-end pipeline to serve Bible passages dynamically via a mock API.
This included:
1. **SQLite Database Schema**: Created a `verses` table in `bible.db` that maps to the data provided in the `.psv` files.
2. **Data Ingestion Script**: `ingest_bible.py` parses all `.psv` files found in the corpus and natively loads them into the DB. The script auto-extracts the book, chapter, and verse references. **Over 127k verses were successfully ingested!**
3. **Advanced Reference Parsing**: Integrated the industry-standard `bcv_parser` (JavaScript) via `py-mini-racer`. This allows for robust parsing of nearly any Bible citation format without needing a local Node.js environment.
4. **Multi-Chapter Support**: The API now correctly handles ranges stretching across chapters (e.g., `Matthew 4:1-5:18`), fetching and concatenating the spans in the correct order.
5. **Streamlined Logic**: Removed the manual `BOOK_MAP` in favor of the parser's built-in normalization, making the service more robust and maintainable.
6. **Dockerization**: The API is fully containerized, including the V8-powered JS engine and optimized in-memory database loading.
7. **Test Frontend**: `index.html` provides a clean UI to input a reference and select a translation.

## How to Verify

### Running with Docker (Recommended)
1. Ensure `bible.db` is in the root directory.
2. Run: `docker-compose up --build`
3. Access the UI via `index.html` or explore the API at `http://localhost:8000`.

### Running with Python (Manual)
1. **Install requirements**: `pip install -r requirements.txt`
2. **Run the API**: `python api.py`
3. **Test the UI**: Open `index.html` and search for e.g. `Matthew 4:1-11`.
