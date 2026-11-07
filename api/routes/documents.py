import shutil
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from api.deps import check_scope
from src import config, library

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents():
    return [{"source": s, "name": Path(s).name} for s in library.list_sources()]


@router.post("")
def upload(files: list[UploadFile] = File(...)):
    known = set(library.list_sources())
    added, skipped = [], []
    for f in files:
        name = Path(f.filename or "").name
        dest = config.LIB_DIR / name
        if not name.lower().endswith(".pdf"):
            skipped.append(f"{name or 'file'}: not a PDF")
        elif str(dest) in known:
            skipped.append(f"{name}: already in the library")
        else:
            with open(dest, "wb") as out:
                shutil.copyfileobj(f.file, out)
            if library.index_pdf(dest):
                added.append(name)
            else:
                dest.unlink(missing_ok=True)
                skipped.append(f"{name}: no readable text")
    return {"added": added, "skipped": skipped}


@router.delete("")
def remove(source: str):
    check_scope(source)
    library.remove_source(source)
    return {"removed": source}
