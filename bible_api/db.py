"""Database helpers and reference parsing."""

import sqlite3
import threading
from pathlib import Path
import re
import json

from .config import DB_PATH, LOAD_IN_MEMORY, SHARED_MEM_URI

thread_local = threading.local()


def get_db():
    """Return a thread-local sqlite3 connection."""
    if not hasattr(thread_local, "connection"):
        if LOAD_IN_MEMORY:
            thread_local.connection = sqlite3.connect(
                f"{SHARED_MEM_URI}&mode=ro&immutable=1", uri=True, check_same_thread=False
            )
        else:
            thread_local.connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        thread_local.connection.row_factory = sqlite3.Row
    return thread_local.connection


# bcv parser is somewhat heavy; keep it global and initialize once.
_bcv_parser = None


def init_bcv_parser():
    """Initialize and return a singleton JS bcv parser."""
    global _bcv_parser
    if _bcv_parser is not None:
        return _bcv_parser

    js_path = Path("en_bcv_parser.js")
    if js_path.exists():
        from py_mini_racer.py_mini_racer import MiniRacer

        with open(js_path, "r", encoding="utf-8") as f:
            js_code = f.read()

        _bcv_parser = MiniRacer()
        _bcv_parser.eval(js_code)
        _bcv_parser.eval("bcv = new bcv_parser()")
        _bcv_parser.eval(
            'bcv.set_options({ "consecutive_combination_strategy": "separate", "osis_compaction_strategy": "bc", "sequence_combination_strategy": "separate" });'
        )

    return _bcv_parser


def parse_ref_cached(ref_str: str):
    """Parse a reference using the JS bcv parser and cache results."""
    parser = init_bcv_parser()
    if not parser:
        return []
    safe_ref = ref_str.replace("'", "\\'")
    js_cmd = (
        "JSON.stringify(bcv.parse('" + safe_ref + "').parsed_entities().map(entity => ({ osis: entity.osis, start: entity.start, end: entity.end })))"
    )
    res_json = parser.eval(js_cmd)
    return json.loads(str(res_json))


def parse_ref(ref_str: str):
    """Parse a reference into a normalized set of bounds for query."""
    # Fast-path for OSIS references
    if ref_str.startswith("osis:"):
        ref_text = ref_str[5:]
        parts = ref_text.split("-")

        def parse_osis_part(part):
            match = re.match(r'^([1-3]?[A-Za-z]+)\.(\d+)(?:\.(\d+))?$', part)
            if not match:
                return None
            book = match.group(1)
            chapter = int(match.group(2))
            verse = int(match.group(3)) if match.group(3) else None
            return {"b": book, "c": chapter, "v": verse}

        start_entity = parse_osis_part(parts[0])
        if not start_entity:
            return None

        if len(parts) > 1:
            end_entity = parse_osis_part(parts[1])
            if not end_entity:
                return None
        else:
            end_entity = start_entity.copy()

        return {
            "book": start_entity["b"],
            "c_start": start_entity["c"],
            "v_start": start_entity["v"] if start_entity["v"] is not None else 1,
            "c_end": end_entity["c"],
            "v_end": end_entity["v"] if end_entity["v"] is not None else 999,
        }

    try:
        entities = parse_ref_cached(ref_str)
        if not entities:
            return None
        entity = entities[0]
        return {
            "book": entity["start"]["b"],
            "c_start": entity["start"]["c"],
            "v_start": entity["start"]["v"],
            "c_end": entity["end"]["c"],
            "v_end": entity["end"]["v"],
        }
    except Exception:
        return None
