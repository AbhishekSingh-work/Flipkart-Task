from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional
from app.db import db_session
from app.schemas import ReportResponse
from app.crud import get_verifications_report

router = APIRouter(prefix="/api/reporting", tags=["reporting"])

@router.get("/report", response_model=ReportResponse)
def generate_report(
    start_date: Optional[str] = Query(
        None, 
        description="Start date in YYYY-MM-DD format (defaults to 7 days ago)"
    ),
    end_date: Optional[str] = Query(
        None, 
        description="End date in YYYY-MM-DD format (defaults to today)"
    )
):
    """
    Retrieves verification records and aggregated summary statistics in the specified date range.
    """
    # 1. Apply default values if dates are missing
    if not start_date:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    # 2. Validate format
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD (e.g., 2026-06-07)."
        )

    # 3. Ensure start date is before or equal to end date
    if start_dt > end_dt:
        raise HTTPException(
            status_code=400, 
            detail="Start date cannot be after end date."
        )

    # 4. Fetch the report from database
    with db_session() as conn:
        try:
            report = get_verifications_report(conn, start_date, end_date)
            return report
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate report: {str(e)}"
            )
