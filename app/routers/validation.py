import os
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from app.config import TEMP_DIR
from app.db import db_session
from app.schemas import ProductResponse, VerificationResponse
from app.s3_helper import upload_verification_image
from app.crud import (
    get_product, 
    log_verification
)

router = APIRouter(prefix="/api/validation", tags=["validation"])

@router.get("/product/{wid}", response_model=ProductResponse)
def lookup_product(wid: str):
    """
    Looks up a product by its Warehouse ID (WID) to display details.
    """
    with db_session() as conn:
        product = get_product(conn, wid.strip())
        if not product:
            raise HTTPException(
                status_code=404, 
                detail=f"Product with WID '{wid}' not found in inventory."
            )
        return product

@router.post("/verify", response_model=VerificationResponse)
async def verify_product(
    wid: str = Form(..., description="Unique Warehouse ID"),
    operator_name: str = Form(..., description="Name of the operator checking the product"),
    image: Optional[UploadFile] = File(None)
):
    """
    Logs a verification event.
    Uploads the physical product image to AWS S3 (falls back to local filesystem).
    """
    wid_clean = wid.strip()
    operator_clean = operator_name.strip()
    
    # 1. Check if product exists in system first
    with db_session() as conn:
        product = get_product(conn, wid_clean)
        if not product:
            raise HTTPException(
                status_code=404, 
                detail=f"Cannot log verification. Product with WID '{wid_clean}' does not exist."
            )

    # 2. Process physical product image upload if present
    image_url = None
    if image:
        # Generate a unique filename: {wid}_{timestamp}.{ext}
        ext = os.path.splitext(image.filename)[1] or ".jpg"
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        filename = f"{wid_clean}_{timestamp_str}_{unique_id}{ext}"
        
        # Save uploaded image to temp file first
        temp_path = os.path.join(TEMP_DIR, filename)
        try:
            async with aiofiles.open(temp_path, "wb") as out_file:
                while content := await image.read():
                    await out_file.write(content)
                    
            # Upload to S3 (or local fallback)
            image_url = upload_verification_image(temp_path, filename)
            
        except Exception as e:
            print(f"[Validation Router] Image processing failed: {e}")
            # Do not block verification logging if image upload fails entirely, but report it
            # Or fall back to a local string if it can't write
            image_url = f"/static/uploads/{filename}"
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    # 3. Log verification event in database
    with db_session() as conn:
        try:
            log_data = log_verification(conn, wid_clean, operator_clean, image_url)
            return log_data
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to save verification event: {str(e)}"
            )
