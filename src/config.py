from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = "gemma4:31b-cloud"
NUM_CTX = 16384
CREATIVE_TEMPERATURE = 0.5

DATA_DIR = BASE_DIR / "data"
LIB_DIR = BASE_DIR / "library"
CHROMA_DIR = str(BASE_DIR / "chroma_db")

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
    folder.mkdir(exist_ok=True)
