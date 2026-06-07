import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "inventory.db"))
DATABASE_DIR = Path(DATABASE_PATH).parent
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Directories
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "app" / "static" / "uploads"))
TEMP_DIR = os.getenv("TEMP_DIR", str(BASE_DIR / "data" / "temp"))

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

# Celery / Redis
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Check if Redis is running, fallback to Celery eager mode (synchronous execution) if it's not
REDIS_AVAILABLE = False
try:
    import redis
    # Parse broker URL to connect
    r = redis.Redis.from_url(CELERY_BROKER_URL, socket_timeout=1.0)
    r.ping()
    REDIS_AVAILABLE = True
except Exception:
    pass

CELERY_ALWAYS_EAGER = os.getenv("CELERY_ALWAYS_EAGER", str(not REDIS_AVAILABLE)).lower() in ("true", "1", "yes")

# AWS S3 Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Performance Settings
CHUNK_SIZE = int(os.getenv("INGESTION_CHUNK_SIZE", "50000"))

# Demo authentication users for the interview build.
# Format: username=password:role:Display Name
DEFAULT_AUTH_USERS = (
    "operator=operator123:operator:Floor Operator,"
    "admin=admin123:admin:Warehouse Admin"
)
AUTH_USERS = os.getenv("AUTH_USERS", DEFAULT_AUTH_USERS)
