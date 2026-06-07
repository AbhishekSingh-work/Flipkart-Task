import os
import uuid
import csv
import io
import aiofiles
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends
from typing import List
from app.config import TEMP_DIR
from app.db import db_session
from app.auth import AuthUser, require_permissions
from app.schemas import IngestionJobResponse
from app.celery_app import process_csv_ingestion
from app.crud import (
    create_ingestion_job, 
    get_ingestion_job, 
    get_recent_ingestion_jobs
)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
require_ingestion_access = require_permissions(["ingestion"])

@router.post("/upload", response_model=IngestionJobResponse)
async def upload_csv(
    file: UploadFile = File(...),
    _: AuthUser = Depends(require_ingestion_access)
):
    """
    Uploads a CSV file containing product data.
    Validates headers immediately, saves the file, and dispatches an async Celery task.
    """
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # 1. Read the beginning of the file to validate headers immediately
    try:
        header_bytes = await file.read(4096)
        await file.seek(0)
        
        header_str = header_bytes.decode("utf-8-sig", errors="ignore")
        csv_reader = csv.reader(io.StringIO(header_str))
        try:
            headers = next(csv_reader)
        except StopIteration:
            raise HTTPException(status_code=400, detail="CSV file is empty.")
            
        headers_lower = [h.strip().lower() for h in headers]
        if "wid" not in headers_lower:
            raise HTTPException(status_code=400, detail="Missing required column: 'WID'")
        if "ean" not in headers_lower:
            raise HTTPException(status_code=400, detail="Missing required column: 'EAN'")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV layout: {str(e)}")

    # 2. Generate unique job ID and file path
    job_id = str(uuid.uuid4())
    temp_file_path = os.path.join(TEMP_DIR, f"{job_id}.csv")

    # 3. Stream upload file to disk chunk-by-chunk to save RAM
    try:
        async with aiofiles.open(temp_file_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # 4. Count estimated lines in file for total progress tracking
    # (Since file is written, this is fast and disk-based)
    line_count = 0
    try:
        with open(temp_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            for _ in f:
                line_count += 1
        line_count = max(0, line_count - 1) # Subtract header
    except Exception:
        line_count = 0

    # 5. Create job in Database and trigger Celery task
    with db_session() as conn:
        create_ingestion_job(conn, job_id, line_count)
        job_data = get_ingestion_job(conn, job_id)

    # Trigger async processing task
    process_csv_ingestion.delay(job_id, temp_file_path)

    return job_data

@router.get("/status/{job_id}", response_model=IngestionJobResponse)
def get_job_status(job_id: str, _: AuthUser = Depends(require_ingestion_access)):
    """
    Checks the status and completion percentage of an ingestion job.
    """
    try:
        with db_session() as conn:
            job = get_ingestion_job(conn, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job ID not found.")
            return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

@router.get("/recent", response_model=List[IngestionJobResponse])
def list_recent_jobs(
    limit: int = 5,
    _: AuthUser = Depends(require_ingestion_access)
):
    """
    Lists recent CSV ingestion activities.
    """
    try:
        with db_session() as conn:
            return get_recent_ingestion_jobs(conn, limit)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list recent jobs: {str(e)}"
        )
