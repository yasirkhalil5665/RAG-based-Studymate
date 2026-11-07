import threading
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader

from src import config
from src.vectorstore import splitter, store

_lock = threading.Lock()


def list_sources():
    metas = store.get(include=["metadatas"])["metadatas"]
    return sorted({m["source"] for m in metas if m and "source" in m})


def index_pdf(path):
    try:
        pages = PyPDFLoader(str(path)).load()
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return False
    chunks = [c for c in splitter.split_documents(pages) if c.page_content.strip()]
    if not chunks:
        return False
    with _lock:
        store.add_documents(chunks)
    return True


def index_folder(folder):
    folder = Path(folder)
    known = set(list_sources())
    added = 0
    for pdf in sorted(folder.rglob("*.pdf")):
        if str(pdf) not in known and index_pdf(pdf):
            added += 1
    return added


def remove_source(source):
    ids = store.get(where={"source": source})["ids"]
    if ids:
        store.delete(ids=ids)
    path = Path(source)
    if path.exists() and path.parent.resolve() == config.LIB_DIR.resolve():
        path.unlink()
