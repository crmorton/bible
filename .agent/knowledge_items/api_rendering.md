# Bible API Rendering Logic

## Overview
The Bible API (`api.py`) reconstructs high-fidelity HTML from atomized spans stored in the database.

## DOM Reconstruction State Machine
The `get_passage` endpoint implements a state machine to manage nested HTML tags:
- **Path Traversal**: Compare the DOM `path` of the current span with the `path` of the previous span.
- **Tag Management**: Automatically closes tags that are no longer in the path and opens new ones.
- **Poetry Handling**: Specifically detects changes in paragraph hashes (`para_md5`) within poetry blocks (`div.poetry`) to insert `<br>` tags, preserving the original line-break structure.

## Dynamic Wrapping
To optimize database storage, high-level redundant containers are excluded from the database and injected dynamically at the API layer:
- `div.passage-text`
- `div.passage-content.passage-class-0`
- `div.version-{translation}` (e.g., `version-LEB`)

This ensures that the global CSS (`base.css`) applies correctly to the served fragments while keeping the database compact.

## Global Scaling & Edge Caching
To support 10M+ daily requests, the API is fronted by a **Cloudflare Load Balancer**.
- **Edge Caching**: The API explicitly sets `Cache-Control: public, max-age=86400` (24 hours). This allows Cloudflare to serve repetitive requests (like "John 3:16") directly from the edge location nearest to the user, bypassing the GCP origin entirely.
- **Geo-Steering**: Cloudflare routes traffic to the nearest healthy GCP Cloud Run region (`us-central1`, `europe-west4`, `asia-northeast1`, or `australia-southeast1`).

## Performance
- **In-Memory SQLite**: The entire `bible_v2.db` is loaded into RAM on startup.
- **Stateless & Portable**: The database is "baked-in" to the production Docker image, making the container entirely self-contained and ready for instant scaling on Cloud Run.
