import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.schemas import ProductResponse, VerificationResponse, VerificationSummary

def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Attempts to parse various date string formats and returns a datetime object.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Clean the string
    cleaned = date_str.strip()
    
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y", 
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%b %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None

def standardize_date(date_str: str) -> Optional[str]:
    """
    Standardizes a date string to YYYY-MM-DD. If it cannot be parsed, returns the original.
    """
    dt = parse_date_string(date_str)
    if dt:
        return dt.strftime("%Y-%m-%d")
    return date_str

def calculate_expiry_details(expiry_date_str: Optional[str]) -> Dict[str, Any]:
    """
    Calculates if a product is expired, days to expiry, and provides a status label.
    """
    if not expiry_date_str:
        return {"is_expired": False, "days_to_expiry": None, "status_label": "Unknown"}
    
    dt = parse_date_string(expiry_date_str)
    if not dt:
        return {"is_expired": False, "days_to_expiry": None, "status_label": "Unknown"}
    
    # Calculate days difference from today (at midnight)
    today = datetime.now()
    today_midnight = datetime(today.year, today.month, today.day)
    expiry_midnight = datetime(dt.year, dt.month, dt.day)
    
    delta = (expiry_midnight - today_midnight).days
    
    if delta < 0:
        return {"is_expired": True, "days_to_expiry": delta, "status_label": "Expired"}
    elif delta <= 30:
        return {"is_expired": False, "days_to_expiry": delta, "status_label": "Expiring Soon"}
    else:
        return {"is_expired": False, "days_to_expiry": delta, "status_label": "Good"}

# --- Products CRUD ---

def get_product(conn: sqlite3.Connection, wid: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single product by its unique Warehouse ID (WID).
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT wid, ean, manufacturing_date, expiry_date FROM products WHERE wid = ?", 
        (wid,)
    )
    row = cursor.fetchone()
    if row:
        prod_dict = dict(row)
        expiry_info = calculate_expiry_details(prod_dict["expiry_date"])
        prod_dict.update(expiry_info)
        return prod_dict
    return None

def bulk_insert_products(conn: sqlite3.Connection, products_data: List[tuple]) -> int:
    """
    Performs a high-performance batch insert or replace.
    Expects products_data as a list of tuples: (wid, ean, mfg_date, exp_date)
    """
    cursor = conn.cursor()
    # Using INSERT OR REPLACE to overwrite duplicate WIDs as inventory status changes
    cursor.executemany(
        """
        INSERT OR REPLACE INTO products (wid, ean, manufacturing_date, expiry_date)
        VALUES (?, ?, ?, ?)
        """,
        products_data
    )
    return cursor.rowcount

# --- Ingestion Jobs CRUD ---

def create_ingestion_job(conn: sqlite3.Connection, job_id: str, total_rows: int) -> None:
    """
    Registers a new ingestion background task job.
    """
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO ingestion_jobs (job_id, status, total_rows, processed_rows, created_at)
        VALUES (?, 'PENDING', ?, 0, ?)
        """,
        (job_id, total_rows, now_str)
    )

def update_ingestion_job(
    conn: sqlite3.Connection, 
    job_id: str, 
    processed_rows: int, 
    status: str, 
    error_message: Optional[str] = None
) -> None:
    """
    Updates progress or completion status of an ingestion job.
    """
    cursor = conn.cursor()
    now_str = datetime.now().isoformat() if status in ("COMPLETED", "FAILED") else None
    
    if now_str:
        cursor.execute(
            """
            UPDATE ingestion_jobs 
            SET processed_rows = ?, status = ?, error_message = ?, completed_at = ?
            WHERE job_id = ?
            """,
            (processed_rows, status, error_message, now_str, job_id)
        )
    else:
        cursor.execute(
            """
            UPDATE ingestion_jobs 
            SET processed_rows = ?, status = ?
            WHERE job_id = ?
            """,
            (processed_rows, status, job_id)
        )

def get_ingestion_job(conn: sqlite3.Connection, job_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches job details and computes the percentage of completion.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT job_id, status, total_rows, processed_rows, error_message, created_at, completed_at 
        FROM ingestion_jobs WHERE job_id = ?
        """,
        (job_id,)
    )
    row = cursor.fetchone()
    if row:
        job = dict(row)
        total = job["total_rows"]
        processed = job["processed_rows"]
        job["percent_complete"] = round((processed / total) * 100, 2) if total > 0 else 0.0
        return job
    return None

def get_recent_ingestion_jobs(conn: sqlite3.Connection, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Returns the most recent ingestion jobs.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT job_id, status, total_rows, processed_rows, error_message, created_at, completed_at 
        FROM ingestion_jobs ORDER BY created_at DESC LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    jobs = []
    for r in rows:
        job = dict(r)
        total = job["total_rows"]
        processed = job["processed_rows"]
        job["percent_complete"] = round((processed / total) * 100, 2) if total > 0 else 0.0
        jobs.append(job)
    return jobs

# --- Verifications CRUD ---

def log_verification(
    conn: sqlite3.Connection, 
    wid: str, 
    operator_name: str, 
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Logs a physical product validation event.
    """
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO verifications (wid, operator_name, timestamp, image_path)
        VALUES (?, ?, ?, ?)
        """,
        (wid, operator_name, timestamp, image_path)
    )
    ver_id = cursor.lastrowid
    
    # Return the newly logged verification data joined with the product information
    cursor.execute(
        """
        SELECT v.id, v.wid, v.operator_name, v.timestamp, v.image_path,
               p.ean, p.manufacturing_date, p.expiry_date
        FROM verifications v
        LEFT JOIN products p ON v.wid = p.wid
        WHERE v.id = ?
        """,
        (ver_id,)
    )
    row = cursor.fetchone()
    data = dict(row)
    expiry_info = calculate_expiry_details(data["expiry_date"])
    data.update(expiry_info)
    return data

def get_verifications_report(
    conn: sqlite3.Connection, 
    start_date: str, 
    end_date: str
) -> Dict[str, Any]:
    """
    Generates a report of verification activities within a date range (inclusive).
    Supports dates formatted as YYYY-MM-DD.
    """
    cursor = conn.cursor()
    
    # Standardize inputs to match SQLite comparison
    # Add time bounds: start from 00:00:00 and end at 23:59:59
    start_dt = f"{start_date}T00:00:00"
    end_dt = f"{end_date}T23:59:59"
    
    cursor.execute(
        """
        SELECT v.id, v.wid, v.operator_name, v.timestamp, v.image_path,
               p.ean, p.manufacturing_date, p.expiry_date
        FROM verifications v
        LEFT JOIN products p ON v.wid = p.wid
        WHERE v.timestamp >= ? AND v.timestamp <= ?
        ORDER BY v.timestamp DESC
        """,
        (start_dt, end_dt)
    )
    rows = cursor.fetchall()
    
    activities = []
    good_count = 0
    expiring_soon_count = 0
    expired_count = 0
    mismatch_count = 0
    
    for r in rows:
        data = dict(r)
        expiry_info = calculate_expiry_details(data["expiry_date"])
        data.update(expiry_info)
        
        # Calculate stats
        status = expiry_info["status_label"]
        if status == "Expired":
            expired_count += 1
        elif status == "Expiring Soon":
            expiring_soon_count += 1
        else:
            good_count += 1
            
        # If product info is missing, it's a structural discrepancy
        if not data["ean"]:
            mismatch_count += 1
            data["status_label"] = "Data Mismatch"
            
        activities.append(data)
        
    summary = {
        "total_verifications": len(activities),
        "good_count": good_count,
        "expiring_soon_count": expiring_soon_count,
        "expired_count": expired_count,
        "mismatch_count": mismatch_count
    }
    
    return {
        "summary": summary,
        "activities": activities
    }
