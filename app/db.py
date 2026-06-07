import sqlite3
from contextlib import contextmanager
from app.config import DATABASE_PATH

def get_db_conn():
    """
    Creates and returns a tuned SQLite connection.
    Enables WAL mode, configures cache sizes, and enforces foreign key constraints.
    """
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    # Enable Write-Ahead Log (WAL) mode for concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    # Normal synchronous mode is safe with WAL and faster
    conn.execute("PRAGMA synchronous=NORMAL;")
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys=ON;")
    # Set cache size to ~64MB (negative values indicate KB, i.e., -64000 = 64000 KB)
    conn.execute("PRAGMA cache_size=-64000;")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_session():
    """
    Context manager for database transactions.
    Handles commits and rollbacks automatically.
    """
    conn = get_db_conn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """
    Initializes the database schema and creates optimized indexes.
    """
    with db_session() as conn:
        # Create products table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                wid TEXT PRIMARY KEY,
                ean TEXT NOT NULL,
                manufacturing_date TEXT,
                expiry_date TEXT
            ) WITHOUT ROWID;
        """)
        # Create indexes on products
        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_ean ON products(ean);")

        # Create verifications logging table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wid TEXT NOT NULL,
                operator_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                image_path TEXT,
                FOREIGN KEY (wid) REFERENCES products(wid)
            );
        """)
        # Create indexes on verifications
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verifications_timestamp ON verifications(timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verifications_wid ON verifications(wid);")

        # Create ingestion jobs status tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                total_rows INTEGER DEFAULT 0,
                processed_rows INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
        """)
        
        print("Database initialized successfully with WAL and RowID optimization.")

if __name__ == "__main__":
    init_db()
