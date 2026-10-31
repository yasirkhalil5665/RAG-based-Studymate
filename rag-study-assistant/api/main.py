from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from api.routes import chat, documents, study
from src import config, library

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    added = await run_in_threadpool(library.index_folder, config.DATA_DIR)
    if added:
        print(f"Indexed {added} new PDF(s) from {config.DATA_DIR}")
    yield


app = FastAPI(title="Study Assistant", lifespan=lifespan)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(study.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception):
    return JSONResponse({"detail": f"{type(exc).__name__}: {exc}"}, status_code=500)
