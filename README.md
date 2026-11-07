# Studymate

Chat with your lecture PDFs, and turn them into flashcards, quizzes and summaries. Answers come only from your documents and show the source pages. Everything runs on your computer: Ollama for the language model, Chroma for the vector database.

## Structure

```
RAG_based_Studymate/
├── src/
│   ├── config.py        all settings
│   └── rag.py           all the logic: indexing, search, chat, cards, quiz, summary
├── api/
│   ├── main.py          the FastAPI server (routes)
│   └── UI/              index.html, style.css, app.js
├── notebook/all.ipynb   the same chat pipeline, step by step
├── tests/smoke_test.py  checks the running server
├── data/                put your PDFs here
└── requirements.txt
```

## Setup

```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ollama must be running with the model named in `src/config.py`.

## Run

From the project folder (not from inside `api/`):

```
uvicorn api.main:app
```

Open http://localhost:8000. Do not double-click `index.html`; it only works through the server.

PDFs in `data/` are indexed at startup. You can also add PDFs with the **Add PDFs** button. The first start is slow because models download and PDFs are embedded.

## Test

1. Start the server.
2. In a second terminal, from the project folder:

```
python tests/smoke_test.py
```

It checks the library, chat with sources, follow-up memory, scoping to one document, flashcards, quiz, summary and error handling, then prints PASS or FAIL for each. It reads real answers, so it takes a few minutes with a real model.

Then try the page by hand:
- Ask a question, open a source chip, and confirm the passage is on that page of the PDF.
- Ask a follow-up using "it" or "that" and check it still makes sense.
- Pick one document in Study scope and confirm answers cite only that file.
- Generate flashcards, a quiz and a summary.
- Add a PDF with the button, then remove it.

## Settings

All in `src/config.py`: model names, chunk size and overlap, how many chunks go to the model, and the limits for cards and summaries. Restart after editing. Chunk settings apply to PDFs indexed afterwards; delete `chroma_db/` to re-index everything.

## Notes

- Scanned PDFs (pictures of pages) have no text and cannot be indexed. The server prints `Skipped ...: no readable text` for them. Slides that are mostly images give weak answers too.
- Removing a document that lives in `data/` only removes it from the index. It returns at the next start unless you delete the file.
- Chat memory is kept in server memory and is cleared on restart.
- There is no login. Keep the server on `localhost`.
