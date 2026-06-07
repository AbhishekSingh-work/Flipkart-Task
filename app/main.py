import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.db import init_db
from app.routers import ingestion, validation, reporting
from app.config import UPLOAD_DIR, BASE_DIR

# 1. Initialize database on module load or import
init_db()

# 2. Setup FastAPI application
app = FastAPI(
    title="Product Verification System",
    description="Bulk ingestion, on-the-floor physical verification, and QA auditing reports.",
    version="1.0.0"
)

# 3. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits all local/development requests
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include API Routers
app.include_router(ingestion.router)
app.include_router(validation.router)
app.include_router(reporting.router)

# 5. Serve static uploads (captured verification images)
# Check if uploads dir exists
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# 6. Route to serve frontend index.html at root url
@app.get("/")
async def serve_index():
    index_path = BASE_DIR / "app" / "static" / "index.html"
    if not index_path.exists():
        # Temporary placeholder if index.html is still being written
        return {"message": "Server is running. Frontend index.html not found yet."}
    return FileResponse(str(index_path))

print("[Backend App] FastAPI application started and ready.")
