import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR))

EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:31b-cloud")
NUM_CTX = int(os.getenv("NUM_CTX", "16384"))
CREATIVE_TEMPERATURE = 0.5

APP_USER = os.getenv("APP_USER", "studymate")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
LIB_DIR = STORAGE_DIR / "library"
CHROMA_DIR = str(STORAGE_DIR / "chroma_db")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

OCR_ENABLED = True
OCR_MIN_CHARS = 40
OCR_ZOOM = 2.0

SEARCH_K = 10
CANDIDATES = 20
TOP_K = 5
NEIGHBOR_PAGES = 1
MAX_CONTEXT_CHARS = 14000
HISTORY_TURNS = 3

STUDY_CHUNKS = 8
MIN_STUDY_CHARS = 150
MAX_ITEMS = 30
SUMMARY_BATCH_CHARS = 6000

for folder in (DATA_DIR, LIB_DIR):
    folder.mkdir(parents=True, exist_ok=True)

