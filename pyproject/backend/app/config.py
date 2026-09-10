import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DOCS_DIR = DATA_DIR / "docs"
INDEX_DIR = DATA_DIR / "index"
DB_PATH = DATA_DIR / "app.db"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
TOP_K = 5
EMBEDDING_DIM = 128
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 700

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_CSV_ROWS = 8000
MAX_EMBEDDED_ROWS = 2500

USER_LLM_API_KEY = os.getenv("USER_LLM_API_KEY", "")
USER_LLM_BASE_URL = os.getenv("USER_LLM_BASE_URL", "https://api.openai.com/v1")
USER_LLM_MODEL = os.getenv("USER_LLM_MODEL", "gpt-3.5-turbo")
USER_EMBEDDING_MODEL = os.getenv("USER_EMBEDDING_MODEL", "text-embedding-3-small")
API_TOKEN = os.getenv("USER_API_TOKEN", "")

RATE_LIMIT_PER_MIN = 100
RATE_LIMIT_PER_HOUR = 1000
