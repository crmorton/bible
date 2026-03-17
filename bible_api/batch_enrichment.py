"""Batch enrichment utilities for fetching passage HTML and saving to a database."""

import logging

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:  # pragma: no cover
    psycopg2 = None
    execute_batch = None

from .client import BibleAPIClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


DEFAULT_DB_CONFIG = {
    "dbname": "your_database_name",
    "user": "your_username",
    "password": "your_password",
    "host": "localhost",
    "port": "5432",
}


def ensure_psycopg2():
    if psycopg2 is None:
        raise ImportError(
            "The 'psycopg2' package is required for batch enrichment. "
            "Install with: pip install psycopg2-binary"
        )


def setup_database(conn):
    """Create the destination table if it doesn't exist."""
    query = """
    CREATE TABLE IF NOT EXISTS bible_passage_html (
        passage_id INTEGER PRIMARY KEY,
        translation VARCHAR(10),
        html TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_passage FOREIGN KEY (passage_id) REFERENCES bible_passages (id) ON DELETE CASCADE
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)
    conn.commit()
    logging.info("Ensured 'bible_passage_html' table exists.")


def get_pending_passages(conn, batch_size=None):
    """Yield passages that still need enrichment.

    If batch_size is provided, this uses a server-side cursor to stream results.
    """
    base_query = """
        SELECT bp.id, bp.osis
        FROM bible_passages bp
        LEFT JOIN bible_passage_html bph ON bp.id = bph.passage_id
        WHERE bph.passage_id IS NULL
        ORDER BY bp.id
    """

    if batch_size is None:
        with conn.cursor() as cur:
            cur.execute(base_query)
            rows = cur.fetchall()
        for row in rows:
            yield {"id": row[0], "osis": row[1]}
        return

    # Use server-side cursor for streaming larger tables.
    cur = conn.cursor(name="enrichment_cursor")
    cur.itersize = batch_size
    cur.execute(base_query)

    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        for row in rows:
            yield {"id": row[0], "osis": row[1]}

    cur.close()


def save_enriched_passages(conn, results, translation):
    """Save enriched HTML into the database."""
    if execute_batch is None:
        raise ImportError(
            "The 'psycopg2' package is required for saving enrichment results. "
            "Install with: pip install psycopg2-binary"
        )

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    if failed:
        logging.warning(f"{len(failed)} passages failed to fetch. See details above.")
        for f in failed[:5]:
            logging.warning(f"  Failed ID {f.get('id')} ({f.get('osis')}): {f.get('error')}")

    if not successful:
        logging.info("No successful passages to save.")
        return

    query = """
        INSERT INTO bible_passage_html (passage_id, translation, html)
        VALUES (%(id)s, %(translation)s, %(html)s)
        ON CONFLICT (passage_id) DO UPDATE
        SET html = EXCLUDED.html, translation = EXCLUDED.translation;
    """

    insert_data = [
        {"id": res["id"], "translation": translation, "html": res["html"]}
        for res in successful
    ]

    with conn.cursor() as cur:
        execute_batch(cur, query, insert_data)
    conn.commit()

    logging.info(f"Successfully saved {len(insert_data)} passages to the database.")


def run_batch_enrichment(
    db_config=None,
    api_base_url="http://localhost:8000/passage",
    translation="LEB",
    max_workers=50,
    batch_size=10000,
):
    """Run the full enrichment pipeline.

    This is designed to be idempotent: it only processes passages that do not
    yet have HTML stored.
    """
    ensure_psycopg2()

    if db_config is None:
        db_config = DEFAULT_DB_CONFIG.copy()

    logging.info("Connecting to database...")
    conn = psycopg2.connect(**db_config)

    try:
        setup_database(conn)

        # Stream through pending passages and process in chunks
        pending_iter = get_pending_passages(conn, batch_size=batch_size)

        client = BibleAPIClient(base_url=api_base_url, max_workers=max_workers)

        chunk = []
        for passage in pending_iter:
            chunk.append(passage)
            if len(chunk) >= batch_size:
                logging.info(f"Processing chunk of {len(chunk)} passages...")
                results = client.fetch_batch(chunk, translation=translation)
                save_enriched_passages(conn, results, translation)
                conn.commit()
                chunk = []

        if chunk:
            logging.info(f"Processing final chunk of {len(chunk)} passages...")
            results = client.fetch_batch(chunk, translation=translation)
            save_enriched_passages(conn, results, translation)
            conn.commit()

        logging.info("Batch enrichment completed.")

    finally:
        conn.close()
        logging.info("Database connection closed.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enrich passages by fetching HTML from the Bible API.")
    parser.add_argument("--db-name", default=DEFAULT_DB_CONFIG["dbname"], help="Postgres database name")
    parser.add_argument("--db-user", default=DEFAULT_DB_CONFIG["user"], help="Postgres user")
    parser.add_argument("--db-password", default=DEFAULT_DB_CONFIG["password"], help="Postgres password")
    parser.add_argument("--db-host", default=DEFAULT_DB_CONFIG["host"], help="Postgres host")
    parser.add_argument("--db-port", default=DEFAULT_DB_CONFIG["port"], help="Postgres port")
    parser.add_argument("--api-url", default="http://localhost:8000/passage", help="Base URL for the Bible API")
    parser.add_argument("--translation", default="LEB", help="Translation acronym")
    parser.add_argument("--max-workers", type=int, default=50, help="Max worker threads for API calls")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Number of passages to process per chunk (set 0 to disable streaming cursor)",
    )

    args = parser.parse_args()

    batch_size = None if args.batch_size <= 0 else args.batch_size

    db_config = {
        "dbname": args.db_name,
        "user": args.db_user,
        "password": args.db_password,
        "host": args.db_host,
        "port": args.db_port,
    }

    run_batch_enrichment(
        db_config=db_config,
        api_base_url=args.api_url,
        translation=args.translation,
        max_workers=args.max_workers,
        batch_size=batch_size,
    )


if __name__ == "__main__":
    main()
