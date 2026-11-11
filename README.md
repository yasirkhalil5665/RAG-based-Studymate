# Studymate

Chat with your lecture PDFs, and turn them into flashcards, quizzes and summaries. Answers come only from your documents and show the passages they used. Everything runs on your computer: Ollama for the language model, Chroma for the vector database.

## Structure

```
RAG_based_Studymate/
├── src/
│   ├── config.py        all settings
│   └── rag.py           indexing, OCR, search, chat, flashcards, quiz, summary
├── api/main.py          the FastAPI server
├── Dockerfile           builds the app for deployment
├── render.yaml          Render deployment settings
├── UI/                  index.html, style.css, app.js
├── notebook/all.ipynb   a simple version of the chat pipeline, for learning
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

**OCR (recommended).** Many lecture PDFs keep their slides as pictures, so the text is invisible to search. Studymate reads those pages with OCR. It needs the Tesseract program once:

```
sudo dnf install tesseract         # Fedora
sudo apt install tesseract-ocr     # Ubuntu or Debian
brew install tesseract             # Mac
```

Without it the app still works, but picture-only slides cannot be searched. The server prints a message at startup when OCR is off.

Ollama must be running with the model named in `src/config.py`.

## Run

From the project folder:

```
python -m uvicorn api.main:app --port 8080
```

Open http://localhost:8080.

PDFs in `data/` and `library/` are indexed at startup. You can also add PDFs with the **Add PDFs** button. The first start is slow: models download, and OCR takes about one to two seconds per picture-only page (a 130-page scanned PDF takes a couple of minutes, once).

## How a chat answer is made

1. Your question is rewritten to stand on its own if it follows earlier turns.
2. The model fixes spelling and writes two alternative phrasings.
3. Each phrasing is searched two ways: by meaning (embeddings) and by keywords (BM25). The results are merged.
4. A reranker scores the best 20 candidates and keeps the top 5.
5. The slides next to each hit (the page before and after) are added, so the model sees the surrounding explanation.
6. The model answers from those excerpts and cites file and page.

## Settings

All in `src/config.py`. Restart after editing.

- Changing `EMBED_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP` or `OCR_ENABLED` makes the app build a fresh index automatically at the next start. The old index stays in `chroma_db/` and can be deleted.
- `TOP_K`, `NEIGHBOR_PAGES` and `MAX_CONTEXT_CHARS` control how much text the model sees per question.

## Test

With the server running, in a second terminal:

```
python tests/smoke_test.py http://localhost:8080
```

## When you get "I don't know"

Open **Source passages** under the answer.
- If the passages are the wrong slides, the search missed. Try a more specific question, or pick one lecture under Study scope.
- If the passages are the right slides but nearly empty, the content is a diagram or formula that text search cannot read. Only a vision model could.
- If the passages contain the answer, tell the model to try again with a clearer question.

## Deploy to Render

The app is ready for Render with the `Dockerfile` and `render.yaml` in this folder.

1. Put the project in a **private** GitHub repository. Do not commit PDFs (`data/*.pdf` is ignored).
2. In Render, create an **Environment Group** named `studymate-env` (or change the name in `render.yaml`) with:

   | Key | Value |
   |---|---|
   | `OLLAMA_API_KEY` | your key from ollama.com/settings/keys |
   | `APP_PASSWORD` | a long password you choose |
   | `APP_USER` | optional, default is `studymate` |

3. In Render, choose **New > Blueprint**, select the repository, and apply. Render reads `render.yaml`, builds the image, attaches a 5 GB disk at `/data`, and links the group.
4. Open the service URL. The browser asks for the user name and password.
5. Add your PDFs with **Add PDFs**. They are stored on the disk and survive redeploys.

Settings used on Render, set in `render.yaml` (keep each key in one place only):

| Key | Value | Meaning |
|---|---|---|
| `STORAGE_DIR` | `/data` | where the index and uploaded PDFs live (the disk) |
| `OLLAMA_HOST` | `https://ollama.com` | use Ollama's cloud API |
| `LLM_MODEL` | `gemma4:31b` | the name on the API (no `-cloud`) |

The embedding and reranker models are downloaded while the image is built, so a restart does not download them again. The server answers `/health` straight away and indexes documents in the background.

Without `APP_PASSWORD`, anyone with the URL can use the app and your Ollama quota. The server prints a warning at startup when it is not set.

## Notes

- Removing a document in `data/` only removes it from the index; it returns at the next start unless you delete the file.
- Chat memory is kept in server memory and is cleared on restart.
- There is no login. Keep the server on `localhost`.
