# Bible Reference Parsing Strategy

## Overview
The API uses the industry-standard `bcv_parser` to handle the immense variety of Bible reference formats (e.g., "Jn 3:16", "1 John 3.16", "Matthew 4:1-5:18").

## Technology Stack: `py-mini-racer`
Instead of using a local Node.js environment or regex-based maps, the system uses `py-mini-racer` to execute the specialized JavaScript library `en_bcv_parser.js` directly within the Python process.

## Normalization Workflow
The service employs a two-tier parsing strategy:

### 1. OSIS Fast-Path (Machine-Readable)
For requests using the `osis:` prefix (e.g., `osis:Matt.5.8`), the API uses a highly efficient **regex-based fast-path**. 
- **Bypasses JS Engine**: This skips the `MiniRacer` V8 context entirely, significantly reducing latency and CPU usage for automated requests.
- **Scope**: Handles single verses, multi-verse ranges, and chapter-level ranges across the same or different chapters.

### 2. Natural Language Parsing (Human-Readable)
For all other strings (e.g., "John 3:16", "Matt. 4"), the API uses the full **JS `bcv_parser`**.
- **Technology Stack**: Uses `py-mini-racer` to execute `en_bcv_parser.js` within the Python process.
- **Initialisation**: The JS engine is lazily initialized on the first non-OSIS request to conserve resources if only automated requests are received.
- **Robustness**: Native support for diverse abbreviations, numbered books, and complex verse ranges.

## Benefits
- **No Manual Mapping**: Removes the need for a brittle `BOOK_MAP`.
- **Language Aware**: The parser handles complex corner cases (like numbered books and diverse abbreviations) natively.
- **Efficiency**: The V8 engine is initialized once on startup and reused for all requests.
