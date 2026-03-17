"""Bible API core package.

This package contains the core database parsing/rendering logic and helper
utilities. FastAPI application creation is provided by :mod:`bible_api.api`.
"""

from .config import DEFAULT_PORT
from .db import get_db, parse_ref
from .passage import render_passage_html
from .client import BibleAPIClient

__all__ = [
    "DEFAULT_PORT",
    "get_db",
    "parse_ref",
    "render_passage_html",
    "BibleAPIClient",
]
