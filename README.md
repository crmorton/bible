# Bible API

[![CI](https://github.com/crmorton/bible/actions/workflows/python-ci.yml/badge.svg)](https://github.com/crmorton/bible/actions/workflows/python-ci.yml)

A lightweight **Bible passage API** with a built-in UI (served via FastAPI), HTML rendering, and tools for benchmarking and batch enrichment.

## ✅ Quickstart (Windows)

### 1) Create / activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3) Run the server

```powershell
python -m bible_api.api
```

Then open:

- UI: `http://localhost:9091/`
- API docs: `http://localhost:9091/docs`

### 4) Quick start check (optional)

This helper starts the server, confirms the UI responds, then shuts it down.

```powershell
python scripts/quick_start.py
```

> The UI is rendered from `bible_api/ui.py` and uses the scraped `bible-gateway/` CSS.

## 🧪 Tests

Run the full test suite:

```powershell
python -m pytest -q
```

## � Data Ingestion / Translation Metadata

The repository includes helper scripts to ingest scraped HTML into `bible_v2.db` and to scrape translation metadata.

```powershell
python ingest_html.py --data-dir ./bible-gateway/2026 --db-path ./bible_v2.db
python scrape_translations.py --db-path ./bible_v2.db --limit 50
```

## �🧪 Benchmarking

This repository includes a benchmark tool that hits `GET /passage` in parallel.

```powershell
python -m bible_api.benchmark --csv ./tests/data/bible_passages_sample2.csv --url http://localhost:9091/passage --translation LEB --concurrency 25
```

Or, if installed as a console script:

```powershell
bible-api-benchmark --csv ./tests/data/bible_passages_sample2.csv
```

## 🧩 Batch Enrichment (Postgres)

This tool fetches passage HTML from the running API and stores it in a Postgres table.

```powershell
python -m bible_api.batch_enrichment --db-name mydb --db-user myuser --db-password mypass
```

Or as a console script:

```powershell
bible-api-enrich --db-name mydb --db-user myuser --db-password mypass
```

---

## 🧩 Quick Database Download

If you need a fresh `bible_v2.db` (or similar), you can download it via the included helper:

```powershell
python scripts/download_db.py --url https://<your-host>/bible_v2.db --output bible_v2.db
```

You can also set the download URL via environment variable:

```powershell
$env:BIBLE_DB_URL = "https://<your-host>/bible_v2.db"
python scripts/download_db.py
```

## 🚀 Deployment & Windows Service

For production deployment and service hosting, see `DEPLOYMENT.md`.

---

## 🗂️ Notes

- The embedded SQLite data sources are in `bible_2025.db`, `bible_2026.db`, etc.
- The UI assets are in `bible-gateway/`.
- If you want to run as a Windows service, see `deploy/windows-service/bible_server_service.exe` and `deploy/windows-service/WINDOWS_SERVICE.md`.
