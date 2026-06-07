import os
import shutil
import boto3
from app.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_S3_BUCKET,
    AWS_DEFAULT_REGION,
    UPLOAD_DIR
)

def upload_verification_image(local_file_path: str, filename: str) -> str:
    """
    Uploads a verification image to AWS S3.
    If credentials are missing or the upload fails, it falls back to local storage.
    
    Returns:
        The URL of the uploaded image (either an S3 HTTP URL or a local relative path).
    """
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET:
        try:
            print(f"[S3 Helper] Attempting upload of {filename} to bucket {AWS_S3_BUCKET}...")
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_DEFAULT_REGION
            )
            
            # Determine content type based on extension
            content_type = "image/jpeg"
            if filename.lower().endswith(".png"):
                content_type = "image/png"
            elif filename.lower().endswith(".webp"):
                content_type = "image/webp"

            s3_client.upload_file(
                local_file_path,
                AWS_S3_BUCKET,
                filename,
                ExtraArgs={"ContentType": content_type}
            )
            s3_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_DEFAULT_REGION}.amazonaws.com/{filename}"
            print(f"[S3 Helper] Successfully uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            print(f"[S3 Helper] AWS S3 upload failed: {e}. Falling back to local storage.")
    else:
        print("[S3 Helper] AWS S3 credentials not configured. Using local storage fallback.")

    # Fallback to local storage
    dest_path = os.path.join(UPLOAD_DIR, filename)
    try:
        # If the file is not already in the target static upload folder, copy it
        if os.path.abspath(local_file_path) != os.path.abspath(dest_path):
            shutil.copy2(local_file_path, dest_path)
            print(f"[S3 Helper] Copied verification image to local path: {dest_path}")
        return f"/static/uploads/{filename}"
    except Exception as e:
        print(f"[S3 Helper] Failed to copy file locally: {e}")
        # Return fallback placeholder or relative path
        return f"/static/uploads/{filename}"
