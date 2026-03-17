"""Configuration helpers."""

import os
from pathlib import Path

# Default DB path (can be overridden via the DB_PATH env var).
# Defaults to `bible_v2.db` in the repository root.
ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DB_PATH", ROOT_DIR / "bible_v2.db"))
LOAD_IN_MEMORY = os.getenv("LOAD_IN_MEMORY", "false").lower() == "true"
SHARED_MEM_URI = "file:/memdb1?vfs=memdb"

# Default server port (used by the built-in run scripts)
DEFAULT_PORT = int(os.getenv("PORT", "8000"))
