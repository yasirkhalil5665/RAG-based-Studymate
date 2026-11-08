import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src import config, rag

UI_DIR = Path(__file__).parent.parent / "UI"
sessions = {}


class ChatIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    scope: str | None = None


class StudyIn(BaseModel):
    scope: str | None = None
    topic: str = Field(default="", max_length=200)
    n: int = Field(default=10, ge=1, le=config.MAX_ITEMS)


class SummaryIn(BaseModel):
    scope: str
    style: str = "Short overview"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(rag.index_folder, config.DATA_DIR)
    yield


app = FastAPI(title="Studymate", lifespan=lifespan)


@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception):
    return JSONResponse({"detail": f"{type(exc).__name__}: {exc}"}, status_code=500)


def check_scope(scope):
    if scope and scope not in rag.list_sources():
        raise HTTPException(404, "That document is not in the library.")


@app.get("/api/config")
def get_config():
    return {"summary_styles": list(rag.STYLES), "max_items": config.MAX_ITEMS}


@app.get("/api/documents")
def list_documents():
    return [{"source": s, "name": Path(s).name} for s in rag.list_sources()]


@app.post("/api/documents")
def upload(files: list[UploadFile] = File(...)):
    known = set(rag.list_sources())
    added, skipped = [], []
    for f in files:
        name = Path(f.filename or "").name
        dest = config.LIB_DIR / name
        if not name.lower().endswith(".pdf"):
            skipped.append(f"{name or 'file'}: not a PDF")
        elif rag.source_of(dest) in known:
            skipped.append(f"{name}: already in the library")
        else:
            with open(dest, "wb") as out:
                shutil.copyfileobj(f.file, out)
            try:
                chunks = rag.add_pdf(dest)
            except Exception:
                chunks = 0
            if chunks:
                added.append(name)
            else:
                dest.unlink(missing_ok=True)
                skipped.append(f"{name}: no readable text (scanned PDF?)")
    return {"added": added, "skipped": skipped}


@app.delete("/api/documents")
def remove_document(source: str):
    check_scope(source)
    rag.remove_source(source)
    return {"removed": source}


@app.post("/api/chat")
def chat(body: ChatIn):
    check_scope(body.scope)
    history = sessions.setdefault(body.session_id, [])
    question = body.question.strip()
    result = rag.ask(question, body.scope or None, history)
    history.append((question, result["answer"]))
    return result


@app.delete("/api/chat/{session_id}")
def clear_chat(session_id: str):
    sessions.pop(session_id, None)
    return {"cleared": True}


@app.post("/api/flashcards")
def flashcards(body: StudyIn):
    check_scope(body.scope)
    cards = rag.make_cards(body.scope or None, body.topic, body.n)
    if not cards:
        raise HTTPException(502, "Could not generate cards. Try again or use a different topic.")
    return {"cards": cards}


@app.post("/api/quiz")
def quiz(body: StudyIn):
    check_scope(body.scope)
    questions = rag.make_quiz(body.scope or None, body.topic, body.n)
    if not questions:
        raise HTTPException(502, "Could not generate a quiz. Try again or use a different topic.")
    return {"questions": questions}


@app.post("/api/summary")
def summary(body: SummaryIn):
    check_scope(body.scope)
    if body.style not in rag.STYLES:
        raise HTTPException(422, "Unknown summary style.")
    text = rag.summarize(body.scope, body.style)
    if not text:
        raise HTTPException(422, "This document has no readable text.")
    return {"summary": text}


app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
