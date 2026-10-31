# Study Assistant

Chat with your lecture PDFs, and turn them into flashcards, quizzes and summaries. Answers come only from your documents and show the source pages. Everything runs locally: Ollama for the language model, Chroma for the vector database.

## Project structure

```
rag-study-assistant/
├── src/                  core logic (no web code)
│   ├── config.py         all settings
│   ├── models.py         embeddings, LLMs, reranker
│   ├── vectorstore.py    Chroma store and text splitter
│   ├── library.py        add, list and remove PDFs
│   ├── retrieval.py      typo fixing, search, reranking
│   ├── chat.py           question answering with memory
│   ├── study.py          flashcards and quizzes
│   └── summary.py        lecture summaries
├── api/                  FastAPI app
│   ├── main.py           app setup
│   ├── routes/           documents, chat, study endpoints
│   ├── schemas.py        request models
│   └── static/           index.html, styles.css, js/
├── notebooks/all.ipynb   the same RAG chat, step by step
├── data/                 PDFs here are indexed at startup
├── requirements.txt
└── README.md
```

## Setup

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ollama must be installed and running, with access to the model named in `src/config.py`.

## Run the web app

```
uvicorn api.main:app
```

Open http://localhost:8000. API docs are at http://localhost:8000/docs.

Add lectures with the **Add PDFs** button or by dropping files on it. You can also put PDFs in `data/` and restart the server. Do not use `--reload`: it reloads the models on every code change.

## Settings

Everything lives in `src/config.py`: model names, chunk size and overlap, how many chunks are sent to the model, and the limits for cards, quizzes and summaries. Restart the server after editing. Chunk settings only affect PDFs indexed afterwards; delete `chroma_db/` to re-index everything.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/documents` | list documents |
| POST | `/api/documents` | upload and index PDFs |
| DELETE | `/api/documents?source=...` | remove a document |
| POST | `/api/chat` | ask a question (memory per `session_id`) |
| DELETE | `/api/chat/{session_id}` | clear a chat |
| POST | `/api/flashcards` | generate flashcards |
| POST | `/api/quiz` | generate a quiz |
| POST | `/api/summary` | summarize one document |

## Notebook

`notebooks/all.ipynb` is the chat pipeline in one file: load, chunk, embed, retrieve with typo fixing and reranking, answer with memory and sources. It reads PDFs from `data/` and keeps its own database in `notebooks/chroma_db`.

## Notes

- Chat memory is kept in server memory and is cleared on restart.
- Scanned PDFs have no extractable text and cannot be indexed.
- Flashcards and quizzes are written by the model. Check the cited page when unsure.
- There is no login. Keep the server on `localhost` unless you add authentication.
