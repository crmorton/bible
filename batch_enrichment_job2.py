import psycopg2
from psycopg2.extras import execute_batch
from bible_api_client import BibleAPIClient
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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


def process_enrichment():
    client = BibleAPIClient(max_workers=50) # Keep workers reasonable for the DB write speed
    
    conn = psycopg2.connect(**DB_CONFIG)

    setup_database(conn)
    
    try:
        # Create a named cursor for server-side streaming
        # The 'name' argument turns this into a server-side cursor
        cur = conn.cursor(name='enrichment_cursor')
        
        logging.info("Starting stream from database...")
        
        # Select the pending passages
        query = """
            SELECT bp.id, bp.osis 
            FROM bible_passages bp
            LEFT JOIN bible_passage_html bph ON bp.id = bph.passage_id
            WHERE bph.passage_id IS NULL;
        """
        cur.execute(query)

        while True:
            # Fetch just a chunk of records from the server
            rows = cur.fetchmany(CHUNK_SIZE)
            
            if not rows:
                logging.info("All records processed!")
                break
                
            items = [{"id": row[0], "osis": row[1]} for row in rows]
            logging.info(f"Processing chunk of {len(items)} passages...")
            
            # 1. Fetch from API
            results = client.fetch_batch(items, translation=TRANSLATION)
            
            # 2. Save to DB (Chunked)
            save_enriched_passages(conn, results)
            
            # 3. Explicitly commit after every chunk to clear transaction logs
            conn.commit()
            logging.info(f"Chunk finished and committed.")

    except Exception as e:
        logging.error(f"Error during batch processing: {e}")
        conn.rollback()
    finally:
        conn.close()

def save_enriched_passages(conn, results):
    """Saves a chunk of results to the database."""
    successful = [r for r in results if r["success"]]
    if not successful: return

    query = """
        INSERT INTO bible_passage_html (passage_id, translation, html)
        VALUES (%(id)s, %(translation)s, %(html)s)
        ON CONFLICT (passage_id) DO NOTHING;
    """
    
    data = [{"id": res["id"], "translation": TRANSLATION, "html": res["html"]} for res in successful]
    
    with conn.cursor() as cur:
        execute_batch(cur, query, data)

if __name__ == "__main__":
    process_enrichment()