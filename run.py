import uvicorn
import sys
from app.config import REDIS_AVAILABLE, CELERY_ALWAYS_EAGER

def main():
    print("=" * 60)
    print("             APEX LOGISTICS VERIFICATION HUB")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    
    if REDIS_AVAILABLE:
        print("[Redis Status]  CONNECTED (localhost:6379)")
        print("[Celery Mode]   ASYNCHRONOUS (Runs via Celery Worker)")
        print("\n>>> IMPORTANT: To process tasks in the background, run the Celery worker in a separate terminal:")
        print("    .venv\\Scripts\\celery -A app.celery_app worker --loglevel=info -P threads")
    else:
        print("[Redis Status]  DISCONNECTED (Not running on port 6379)")
        print("[Celery Mode]   EAGER FALLBACK (Tasks run synchronously in-process)")
        print("                (No separate worker is needed to process uploads!)")
        
    print("=" * 60)
    print("Starting FastAPI Uvicorn Server on http://localhost:8000...")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    
    # Run Uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
