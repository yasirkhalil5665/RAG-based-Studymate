from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = "gemma4:31b-cloud"
CREATIVE_TEMPERATURE = 0.5

DATA_DIR = BASE_DIR / "data"
LIB_DIR = BASE_DIR / "library"
CHROMA_DIR = str(BASE_DIR / "chroma_db")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TOP_K = 4
SEARCH_K = 6
HISTORY_TURNS = 3

STUDY_CHUNKS = 8
MAX_ITEMS = 30
SUMMARY_BATCH_CHARS = 6000

for folder in (DATA_DIR, LIB_DIR):
    folder.mkdir(exist_ok=True)

