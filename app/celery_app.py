import os
import csv
import traceback
from celery import Celery
from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_ALWAYS_EAGER, CHUNK_SIZE
from app.db import db_session
from app.crud import (
    bulk_insert_products, 
    update_ingestion_job, 
    standardize_date
)

# Initialize Celery app
celery_app = Celery(
    "product_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Apply configurations
celery_app.conf.update(
    task_always_eager=CELERY_ALWAYS_EAGER,
    task_track_started=True,
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC"
)

@celery_app.task(name="app.celery_app.process_csv_ingestion")
def process_csv_ingestion(job_id: str, csv_file_path: str):
    """
    Background Celery task that processes the uploaded CSV file.
    Reads line-by-line to minimize memory consumption, inserts in batches of CHUNK_SIZE,
    and updates the job progress in the database.
    """
    print(f"[Celery Worker] Starting processing of job {job_id} using file: {csv_file_path}")
    
    if not os.path.exists(csv_file_path):
        error_msg = f"CSV file not found at {csv_file_path}"
        print(f"[Celery Worker] Error: {error_msg}")
        with db_session() as conn:
            update_ingestion_job(conn, job_id, 0, "FAILED", error_msg)
        return

    # Phase 1: Count total rows for accurate progress bar
    total_rows = 0
    try:
        with open(csv_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            # Quick count of lines
            for _ in f:
                total_rows += 1
            # Subtract 1 for the header
            total_rows = max(0, total_rows - 1)
            print(f"[Celery Worker] Total records in CSV: {total_rows}")
    except Exception as e:
        error_msg = f"Failed to count lines in CSV: {str(e)}"
        print(f"[Celery Worker] Error: {error_msg}")
        with db_session() as conn:
            update_ingestion_job(conn, job_id, 0, "FAILED", error_msg)
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        return

    # Update total rows in database and change status to PROCESSING
    with db_session() as conn:
        update_ingestion_job(conn, job_id, 0, "PROCESSING")
        # Explicitly update total_rows if needed
        conn.execute("UPDATE ingestion_jobs SET total_rows = ? WHERE job_id = ?", (total_rows, job_id))

    # Phase 2: Process the CSV in batches
    processed_count = 0
    batch = []
    
    try:
        with open(csv_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.reader(f)
            
            # Read header and normalize column names
            try:
                headers = next(reader)
            except StopIteration:
                raise ValueError("CSV file is empty")
                
            headers_lower = [h.strip().lower() for h in headers]
            
            # Map column indices based on header names
            # Expected columns: WID, EAN, Manufacturing_Date, Expiry_Date
            try:
                wid_idx = headers_lower.index("wid")
                ean_idx = headers_lower.index("ean")
            except ValueError as e:
                missing_col = "WID" if "wid" not in headers_lower else "EAN"
                raise ValueError(f"Required column '{missing_col}' is missing in CSV. Found headers: {headers}")
            
            # Optional columns
            mfg_idx = headers_lower.index("manufacturing_date") if "manufacturing_date" in headers_lower else None
            exp_idx = headers_lower.index("expiry_date") if "expiry_date" in headers_lower else None
            
            # Read rows
            for row in reader:
                if not row:
                    continue  # skip empty lines
                
                # Align row to header length
                if len(row) < max(wid_idx, ean_idx) + 1:
                    continue # skip corrupted/incomplete rows
                
                wid = row[wid_idx].strip()
                ean = row[ean_idx].strip()
                
                # Check for empty WID/EAN
                if not wid or not ean:
                    continue
                
                mfg_date = None
                if mfg_idx is not None and mfg_idx < len(row):
                    mfg_date = standardize_date(row[mfg_idx])
                    
                exp_date = None
                if exp_idx is not None and exp_idx < len(row):
                    exp_date = standardize_date(row[exp_idx])
                
                batch.append((wid, ean, mfg_date, exp_date))
                
                # Insert in batches
                if len(batch) >= CHUNK_SIZE:
                    with db_session() as conn:
                        bulk_insert_products(conn, batch)
                        processed_count += len(batch)
                        update_ingestion_job(conn, job_id, processed_count, "PROCESSING")
                    print(f"[Celery Worker] Processed and committed {processed_count} rows...")
                    batch = []
            
            # Insert any remaining records
            if batch:
                with db_session() as conn:
                    bulk_insert_products(conn, batch)
                    processed_count += len(batch)
                batch = []
            
            # Finalize job status
            with db_session() as conn:
                update_ingestion_job(conn, job_id, processed_count, "COMPLETED")
            print(f"[Celery Worker] Job {job_id} COMPLETED. Processed: {processed_count}/{total_rows}")
            
    except Exception as e:
        error_msg = f"Error during CSV processing: {str(e)}"
        print(f"[Celery Worker] Failed: {error_msg}")
        traceback.print_exc()
        with db_session() as conn:
            update_ingestion_job(conn, job_id, processed_count, "FAILED", error_msg)
    finally:
        # Clean up temporary CSV file
        try:
            if os.path.exists(csv_file_path):
                os.remove(csv_file_path)
                print(f"[Celery Worker] Removed temp file: {csv_file_path}")
        except Exception as cleanup_err:
            print(f"[Celery Worker] Failed to remove temp file: {cleanup_err}")
