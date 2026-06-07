from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductBase(BaseModel):
    wid: str
    ean: str
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None

class ProductResponse(ProductBase):
    is_expired: bool
    days_to_expiry: Optional[int] = None
    status_label: str  # e.g., "Expired", "Expiring Soon", "Good"

class VerificationCreate(BaseModel):
    wid: str = Field(..., description="Unique Warehouse ID of the item being checked")
    operator_name: str = Field(..., description="Name or ID of the warehouse operator")

class VerificationResponse(BaseModel):
    id: int
    wid: str
    ean: str
    operator_name: str
    timestamp: str
    image_path: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status_label: str

class IngestionJobResponse(BaseModel):
    job_id: str
    status: str
    total_rows: int
    processed_rows: int
    percent_complete: float
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

class VerificationSummary(BaseModel):
    total_verifications: int
    good_count: int
    expiring_soon_count: int
    expired_count: int
    mismatch_count: Optional[int] = 0

class ReportResponse(BaseModel):
    summary: VerificationSummary
    activities: List[VerificationResponse]
