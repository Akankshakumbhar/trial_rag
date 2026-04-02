import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance_db.sqlite3")

QDRANT_PATH = os.getenv("QDRANT_PATH", str(BASE_DIR / "local_qdrant"))
QDRANT_URL = os.getenv("QDRANT_URL")  # e.g. http://localhost:6333 — if set, use remote
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "financial_documents")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# all-MiniLM-L6-v2 → 384 dims
EMBEDDING_DIMS = int(os.getenv("EMBEDDING_DIMS", "384"))

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

VECTOR_SEARCH_TOP_K = int(os.getenv("VECTOR_SEARCH_TOP_K", "20"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))

# Optional: after first register, set this email and restart to grant Admin role
INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "").strip() or None
