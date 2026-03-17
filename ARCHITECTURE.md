# Podcast Enrichment Platform & Bible API: Architecture & Vision

## Vision
To build a powerful search engine and enrichment platform for theological content (specifically podcasts). By identifying Bible passage references within podcast episode metadata and transcripts, the platform enriches the content with raw Biblical text. This enables deep semantic search, RAG (Retrieval-Augmented Generation), and an enhanced user experience where users can read the referenced text inline in their preferred translation.

## Target State Architecture
The system is composed of three main layers for data storage, retrieval, and presentation:

### 1. Relational Database (PostgreSQL)
* **Purpose:** Stores core podcast data (shows, episodes, host details, metadata).
* **Enrichment Strategy:** Stores the *reference strings* (e.g., "Matt 4:1-11") of identified Bible passages rather than raw HTML. This minimizes database bloat and allows the presentation layer to decide how to style and format the text dynamically.

* **Presentation / Bible API (FastAPI & SQLite)**
  * **Purpose:** Dynamically serves perfectly styled HTML for Bible references.
  * **Stack:** A FastAPI server running a V8 JS engine (`py-mini-racer`) to execute `en_bcv_parser.js`. It reads from a highly optimized SQLite database (`bible.db`).
  * **Robust Parsing**: Uses the industry-standard `bcv_parser` for natural language inputs, and a custom **OSIS Fast-Path** for machine-detectable strings (e.g., `osis:Matt.5.8`) to bypass the JS engine.
  * **Multi-Chapter Support**: Correctly identifies and queries ranges spanning across chapters, reconstructing the DOM across boundaries.
  * **Global Scaling & Multi-Regional Deployment**: 
    * **Containerization**: Use `Dockerfile.prod` to bake the SQLite database directly into the container image for stateless, ultra-portable deployment.
    * **Compute**: Deployed to multiple **Google Cloud Run** regions (`us-central1`, `europe-west4`, `asia-northeast1`, `australia-southeast1`) for low-latency compute.
    * **Edge Entry**: Fronted by a **Cloudflare Load Balancer** with Geo-Steering and aggressive **Edge Caching** (`Cache-Control: public, max-age=86400`) to handle 10M+ daily requests.
  * **In-Memory Optimization**: The entire database is loaded into RAM on startup for ultra-fast performance.
  * **Dockerized Deployment:** Managed via Docker Compose, containerizing the Python service and the JS engine.
  * **Data Source:** Pre-parsed `.psv` files from Bible scrapes, ingested into SQLite via `ingest_bible.py`.
  * **Workflow:** When a user views a podcast episode, the frontend takes the reference string from Postgres and calls the FastAPI service. The API parses the string via JS, queries the SQLite spans, and reconstructs the high-fidelity HTML.

### 3. Vector Database / Semantic Search Engine
* **Purpose:** Enables advanced semantic search across podcast transcripts.
* **Ingestion Pipeline:** An offline batch process that:
  1. Scans transcript chunks for Biblical references.
  2. Queries the SQLite database for the plain text of the referenced verses.
  3. Appends the raw Biblical text to the transcript chunk metadata.
  4. Generates vector embeddings for the combined payload and stores it in the Vector DB.
* **Benefit:** A search query like "relying on God's word for sustenance" will semantically match episodes referencing Matthew 4:4, even if the transcript only explicitly says "As we see in Matt 4:4...".

---

## Architectural Robustness & Trade-offs

During development, we evaluated whether to use the original HTML files with XSLT transformations and an XML database. We chose the **SQLite + Span-level FastAPI** approach for the following reasons:

- **Error Resilience:** Unlike XML/XSLT, where a single malformed tag can break a transformation, SQLite treats each content span as an independent row. A formatting error in one verse does not compromise the availability of the rest of the 1,000,000+ records.
- **Performance at Scale:** With a target of 13 million+ enrichments, the speed of indexed SQL lookups is significantly higher than XML traversal or XSLT execution.
- **Calculated Flexibility:** By storing the "DNA" of the text (spans + path attributes), we can dynamically inject elements like chapter numbers, verse numbers, and indentation spacers in code. This is more maintainable and easier to debug than complex XSLT sheets.
- **Maintainability:** SQL and Python are standard industry tools. This architecture ensures that any developer can jump in and modify the rendering logic without specialized XML database knowledge.

## Key Technical Decisions

### 1. SQLite for Bible Text Storage
**Decision:** Use an indexed SQLite database instead of persisting HTML strings in PostgreSQL.
**Reasoning:** Storing ~13 million dynamically generated HTML snippets in Postgres (for every enriched podcast reference) would consume an estimated 15-30 GB of unnecessary space. SQLite is incredibly fast for read-only lookups. We cast columns like `bg_id` and `para_md5` to `INTEGER` to heavily optimize variable-length storage. An index on `(translation, book, chapter)` ensures sub-millisecond query performance.

### 2. Direct HTML Ingestion
**Decision:** Ingest directly from raw `.html` scrapes using `ingest_html.py` instead of intermediate `.psv` files.
**Reasoning:** Direct HTML parsing allows for higher fidelity capture of structural markers (like `div.poetry`) and better data integrity. The ingestion pipeline uses BeautifulSoup to traverse the DOM and extract contiguous content spans, storing their parent path and paragraph hashes for perfect reconstruction in the API.

### 3. Dynamic HTML Reconstruction
**Decision:** The FastAPI server reconstructs HTML on the fly from the database records.
**Reasoning:** Allows adding targeted features like inline chapter/verse numbers (`<span class="chapternum">`, `<sup class="versenum">`) and handling complex poetic line breaks (`<br>`) dynamically. It also allows users to switch translations on the frontend instantly without complex backend migrations.

---

## Developer Guide

### Running the Bible API
The API provides the HTML shards for the frontend.
```powershell
# Activate the virtual environment
& .venv/Scripts/Activate.ps1

# Run the API server
python -m bible_api.api
```
*Test the application locally at:* `http://127.0.0.1:8000/passage?ref=Matthew%204:1-11&translation=LEB`

### Running with Docker
The API is containerized for easy deployment.
1. Ensure your `bible.db` is present in the root directory.
2. Run the compose stack:
```bash
docker-compose up --build
```
3. The API will be available at `http://localhost:8000`, with the database automatically loaded into memory.

### Re-ingesting Data
If the source HTML files change, or if rendering logic requires new metadata, re-run the ingestion pipeline. It will drop the existing `verses` table and re-populate the millions of rows from scratch.
```powershell
# Activate the virtual environment
& .venv/Scripts/Activate.ps1

# Run the ingestion script
python ingest_html.py
```
