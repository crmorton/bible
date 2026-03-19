import psycopg2
from psycopg2.extras import execute_batch
from api_client import BibleAPIClient
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Configuration ---
DB_CONFIG = {
    "dbname": "your_database_name",
    "user": "your_username",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

TRANSLATION = "LEB"
CHUNK_SIZE = 10000  # Number of rows to process in one memory cycle

def setup_database(conn):
    """Creates the destination table if it doesn't exist."""
    query = """
    CREATE TABLE IF NOT EXISTS bible_passage_html (
        passage_id INTEGER PRIMARY KEY,
        translation VARCHAR(10),
        html TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        -- Assuming your original table is named 'bible_passages'
        CONSTRAINT fk_passage FOREIGN KEY (passage_id) REFERENCES bible_passages (id) ON DELETE CASCADE
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)
    conn.commit()
    logging.info("Ensured 'bible_passage_html' table exists.")

def get_passages_to_enrich(conn):
    """
    Selects OSIS references that DO NOT yet have HTML saved.
    Using a LEFT JOIN makes this script 'Idempotent' (you can run it multiple 
    times safely. If it crashes halfway, it picks up where it left off!)
    """
    query = """
        SELECT bp.id, bp.osis 
        FROM bible_passages bp
        LEFT JOIN bible_passage_html bph ON bp.id = bph.passage_id
        WHERE bph.passage_id IS NULL;
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        
    # Convert tuples to list of dicts for our API client
    return [{"id": row[0], "osis": row[1]} for row in rows]

def save_enriched_passages(conn, results):
    """Uses bulk insertion to quickly save the HTML to PostgreSQL."""
    # Filter out only the successful API calls
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]

    if failed_results:
        logging.warning(f"{len(failed_results)} passages failed to fetch. Check API logs.")
        for f in failed_results[:5]:
            logging.warning(f"  Failed ID {f['id']} ({f['osis']}): {f['error']}")

    if not successful_results:
        logging.info("No successful passages to save.")
        return

    query = """
        INSERT INTO bible_passage_html (passage_id, translation, html)
        VALUES (%(id)s, %(translation)s, %(html)s)
        ON CONFLICT (passage_id) DO UPDATE 
        SET html = EXCLUDED.html, translation = EXCLUDED.translation;
    """
    
    # Prepare data for insertion
    insert_data = [
        {"id": res["id"], "translation": TRANSLATION, "html": res["html"]}
        for res in successful_results
    ]

    with conn.cursor() as cur:
        # execute_batch is highly optimized for inserting arrays of data into Postgres
        execute_batch(cur, query, insert_data)
    conn.commit()
    
    logging.info(f"Successfully saved {len(insert_data)} HTML passages to the database.")

def main():
    try:
        logging.info("Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        
        setup_database(conn)
        
        items_to_fetch = get_passages_to_enrich(conn)
        if not items_to_fetch:
            logging.info("All passages are already enriched! Nothing to do.")
            return

        logging.info(f"Found {len(items_to_fetch)} passages needing enrichment.")
        
        # Initialize our highly-optimized API Client
        client = BibleAPIClient(max_workers=50)
        
        # Fetch the HTML
        results = client.fetch_batch(items_to_fetch, translation=TRANSLATION)
        
        # Save to DB
        save_enriched_passages(conn, results)

    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    main()