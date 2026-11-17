# Studymate

A study assistant for your lecture PDFs. Ask questions, and get answers taken **only from your documents**, with the file and page cited. Studymate can also turn lectures into flashcards, practice quizzes and summaries.

**Live demo:** https://studymate-vfsr.onrender.com/
The demo is password protected (username `studymate`). It runs on a small server, so the first load after a quiet period can take a minute.

## Features

- **Chat with citations.** Every answer shows the source passages it used, so you can check it.
- **Study scope.** Search all documents, or limit the chat to a single lecture.
- **Flashcards, practice quiz, summary.** Generated from the lecture you pick.
- **OCR.** Slides saved as pictures are read with Tesseract, so scanned PDFs are searchable.
- **Math and tables.** Formulas (LaTeX) and tables in answers render properly.
- **Password login** for deployment.

## How it works

1. Your question is rewritten to stand on its own if it follows earlier turns.
2. The model fixes spelling and writes two alternative phrasings.
3. Each phrasing is searched two ways: by meaning (embeddings) and by keywords (BM25), and the results are merged.
4. A reranker scores the best 20 candidates and keeps the top 5.
5. The slides before and after each hit are added, so the model sees the surrounding explanation.
6. The model answers from those excerpts and cites file and page.

## Tech stack

| Part | Choice |
|---|---|
| Server | FastAPI + Uvicorn |
| Language model | Any OpenAI-compatible API; default is Groq (`openai/gpt-oss-120b`) |
| Embeddings | `sentence-transformers/all-mpnet-base-v2` (runs locally) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (runs locally) |
| Vector store | Chroma, plus BM25 for keyword search |
| PDF reading | pypdf, with PyMuPDF + Tesseract for OCR |
| Frontend | Plain HTML, CSS and JavaScript (`UI/`), KaTeX for math |

## Project structure

```
├── src/
│   ├── config.py      all settings
│   └── rag.py         indexing, OCR, search, chat, flashcards, quiz, summary
├── api/main.py        the FastAPI server
├── UI/                index.html, style.css, app.js
├── Dockerfile         builds the app for deployment
├── render.yaml        Render deployment settings
└── requirements.txt
```

## Run locally

**1. Install**

```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. OCR (recommended).** Install Tesseract once:

```
sudo dnf install tesseract         # Fedora
sudo apt install tesseract-ocr     # Ubuntu or Debian
brew install tesseract             # Mac
```

Without it the app still works, but picture-only slides cannot be searched. The server prints a message at startup when OCR is off.

**3. Get a free Groq key** at https://console.groq.com/keys and set it in the same terminal you start the server from:

```
export LLM_API_KEY=your_key_here
export LLM_MODEL=openai/gpt-oss-120b
```

**4. Start**

```
python -m uvicorn api.main:app --port 8080
```

Open http://localhost:8080. Log in with username `studymate` and the password `test123` (the default; set `APP_PASSWORD` to change it).

Add PDFs with the **Add PDFs** button, or put them in `data/`, which is indexed at startup. The first start is slow because models download. OCR takes about one to two seconds per picture-only page, once per file.

## Configuration

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `LLM_API_KEY` | (none) | API key for the language model. **Required.** |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Any OpenAI-compatible endpoint |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Model name on that provider |
| `LLM_MAX_RETRIES` | `6` | Retries when the free tier rate-limits |
| `APP_USER` | `studymate` | Login user name |
| `APP_PASSWORD` | `test123` | Login password. **Change it when deployed.** |
| `STORAGE_DIR` | project folder | Where the index and uploaded PDFs live |

Search and indexing settings (chunk size, how many passages are used, OCR on/off) are in `src/config.py`. Restart after editing. Changing the embedding model, chunk settings or OCR makes the app rebuild its index at the next start.

## Deploy to Render

1. Push the project to GitHub (do not commit `chroma_db/` or your PDFs).
2. In Render choose **New > Blueprint**, select the repository, and apply. Render reads `render.yaml`, builds the Docker image and attaches a 5 GB disk at `/data`.
3. In the service's **Environment** tab set `LLM_API_KEY` and `APP_PASSWORD`. Check that `LLM_BASE_URL` and `LLM_MODEL` match the table above.
4. Open the service URL and add your PDFs with **Add PDFs**. They are stored on the disk and survive redeploys.

Notes for Render:
- `render.yaml` sets `plan: standard`, which is a paid plan with a disk. The embedding and reranker models need more memory than the free plan has.
- Changing an environment variable in the dashboard restarts the app. Editing `render.yaml` later does not update variables on an existing service; change them in the dashboard.
- The embedding and reranker models are downloaded while the image is built, and `/health` answers straight away while documents index in the background.

## Free-tier limits

Groq's free tier limits requests and tokens per minute. Long summaries make many model calls in a row and are the most likely to hit the limit; the app retries automatically and may pause briefly. Check your limits at https://console.groq.com/docs/rate-limits.

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `Missing credentials` at startup | `LLM_API_KEY` is not set in this terminal (or on Render). |
| `404 model_not_found` in chat | The model is not available to your key. Set `LLM_MODEL` to one your account can use. |
| `429` in chat | Free-tier rate limit. Wait a minute. |
| "no readable text" when adding a PDF | The PDF is scanned and OCR is off, or a package is missing. Install Tesseract and run `pip install -r requirements.txt`. |
| "I don't know" answers | Open **Source passages** under the answer. If they are the wrong slides, ask a more specific question or pick one lecture under Study scope. If the content is a diagram or formula picture, text search cannot read it. |
| Math or tables look raw | Hard-refresh the browser with Ctrl+Shift+R. |

## Notes

- Chat memory is kept in server memory and is cleared on restart.
- Removing a document in `data/` only removes it from the index; it returns at the next start unless you delete the file.
- Answers can be wrong. Check the cited passages before relying on them.