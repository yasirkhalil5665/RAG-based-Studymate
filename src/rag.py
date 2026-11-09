import hashlib
import io
import json
import random
import re
import threading
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from src import config

try:
    import pymupdf
    import pytesseract
    from PIL import Image

    pytesseract.get_tesseract_version()
    OCR_READY = config.OCR_ENABLED
except Exception:
    OCR_READY = False
if config.OCR_ENABLED and not OCR_READY:
    print("OCR is off, so image-only slides cannot be read. Install Tesseract "
          "(Fedora: sudo dnf install tesseract) and run: pip install pytesseract pymupdf pillow")

embeddings = HuggingFaceEmbeddings(model_name=config.EMBED_MODEL)
llm = ChatOllama(model=config.LLM_MODEL, temperature=0, num_ctx=config.NUM_CTX)
creative_llm = ChatOllama(model=config.LLM_MODEL, temperature=config.CREATIVE_TEMPERATURE,
                          num_ctx=config.NUM_CTX)
reranker = CrossEncoder(config.RERANK_MODEL)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
)
fingerprint = hashlib.md5(
    f"{config.EMBED_MODEL}|{config.CHUNK_SIZE}|{config.CHUNK_OVERLAP}|{config.OCR_ENABLED}".encode()
).hexdigest()[:10]
store = Chroma(collection_name=f"studymate-{fingerprint}",
               persist_directory=config.CHROMA_DIR, embedding_function=embeddings)
lock = threading.Lock()


# ---------- library ----------
def source_of(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(config.BASE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def list_sources():
    metas = store.get(include=["metadatas"])["metadatas"]
    return sorted({m["source"] for m in metas})


def ocr_weak_pages(path, pages):
    weak = [p for p in pages if len(p.page_content.strip()) < config.OCR_MIN_CHARS]
    if not weak:
        return pages
    print(f"OCR: reading {len(weak)} image-only pages of {Path(path).name}")
    zoom = pymupdf.Matrix(config.OCR_ZOOM, config.OCR_ZOOM)
    with pymupdf.open(str(path)) as pdf:
        for n, page in enumerate(weak, 1):
            image = pdf[page.metadata["page"]].get_pixmap(matrix=zoom)
            text = pytesseract.image_to_string(Image.open(io.BytesIO(image.tobytes("png")))).strip()
            if len(text) > len(page.page_content.strip()):
                page.page_content = text
            if n % 20 == 0:
                print(f"  OCR {n}/{len(weak)}")
    return pages


def add_pdf(path):
    source = source_of(path)
    pages = PyPDFLoader(str(path)).load()
    if OCR_READY:
        pages = ocr_weak_pages(path, pages)
    chunks = [c for c in splitter.split_documents(pages) if c.page_content.strip()]
    for chunk in chunks:
        chunk.metadata["source"] = source
    if chunks:
        with lock:
            store.add_documents(chunks)
    return len(chunks)


def index_folder(folder):
    known = set(list_sources())
    for pdf in sorted(Path(folder).rglob("*.pdf")):
        if source_of(pdf) in known:
            continue
        try:
            count = add_pdf(pdf)
        except Exception as error:
            print(f"Could not read {pdf.name}: {error}")
            continue
        print(f"Indexed {pdf.name}" if count else f"Skipped {pdf.name}: no readable text")


def remove_source(source):
    ids = store.get(where={"source": source})["ids"]
    if ids:
        store.delete(ids=ids)
    path = config.BASE_DIR / source
    if path.parent == config.LIB_DIR:
        path.unlink(missing_ok=True)


# ---------- retrieval----------
TOKEN = re.compile(r"[a-z0-9]+")
keyword_cache = {"key": None, "index": None, "docs": []}


def expand(question):
    out = llm.invoke(
        "Fix the spelling of this question, then write 2 alternative phrasings "
        "using synonyms. Return one per line, nothing else.\n\nQuestion: " + question
    ).content
    return [line.strip() for line in out.split("\n") if line.strip()][:3] or [question]


def keyword_index():
    ids = store.get(include=[])["ids"]
    key = hash(frozenset(ids))
    if key != keyword_cache["key"]:
        data = store.get(include=["documents", "metadatas"])
        docs = [Document(page_content=t, metadata=m)
                for t, m in zip(data["documents"], data["metadatas"])]
        index = BM25Okapi([TOKEN.findall(d.page_content.lower()) for d in docs]) if docs else None
        keyword_cache.update(key=key, index=index, docs=docs)
    return keyword_cache["index"], keyword_cache["docs"]


def keyword_search(query, scope, n):
    index, docs = keyword_index()
    tokens = TOKEN.findall(query.lower())
    if index is None or not tokens:
        return []
    scores = index.get_scores(tokens)
    hits = []
    for i in sorted(range(len(docs)), key=lambda i: scores[i], reverse=True):
        if scores[i] <= 0:
            break
        if scope and docs[i].metadata["source"] != scope:
            continue
        hits.append(docs[i])
        if len(hits) == n:
            break
    return hits


def fuse(rankings):
    scores, docs = {}, {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            docs[doc.page_content] = doc
            scores[doc.page_content] = scores.get(doc.page_content, 0) + 1 / (60 + rank)
    best = sorted(scores, key=scores.get, reverse=True)
    return [docs[key] for key in best[: config.CANDIDATES]]


def rerank(question, docs):
    scores = reranker.predict([(question, d.page_content) for d in docs])
    ranked = sorted(zip(scores, docs), key=lambda pair: pair[0], reverse=True)
    return ranked[: config.TOP_K]


def retrieve(question, scope=None):
    variants = expand(question)
    where = {"source": scope} if scope else None
    rankings = []
    for variant in variants:
        rankings.append(store.similarity_search(variant, k=config.SEARCH_K, filter=where))
        rankings.append(keyword_search(variant, scope, config.SEARCH_K))
    candidates = fuse(rankings)
    ranked = rerank(variants[0], candidates) if candidates else []
    return variants, ranked


def neighbors(doc):
    page = doc.metadata.get("page", 0)
    pages = list(range(page - config.NEIGHBOR_PAGES, page + config.NEIGHBOR_PAGES + 1))
    data = store.get(
        where={"$and": [{"source": doc.metadata["source"]}, {"page": {"$in": pages}}]},
        include=["documents", "metadatas"],
    )
    return [Document(page_content=t, metadata=m) for t, m in zip(data["documents"], data["metadatas"])]


def build_context(ranked):
    chosen, seen, size = [], set(), 0

    def add(doc):
        nonlocal size
        key = (doc.metadata["source"], doc.metadata.get("page", 0), doc.page_content)
        if key in seen or size + len(doc.page_content) > config.MAX_CONTEXT_CHARS:
            return
        seen.add(key)
        chosen.append(doc)
        size += len(doc.page_content)

    for _, doc in ranked:
        add(doc)
    if config.NEIGHBOR_PAGES:
        for _, doc in ranked:
            for near in neighbors(doc):
                add(near)
    chosen.sort(key=lambda d: (d.metadata["source"], d.metadata.get("page", 0)))
    return chosen


# ---------- chat ----------
prompt = ChatPromptTemplate.from_template(
    "You are a study assistant. Answer the question using the lecture excerpts below. "
    "The excerpts come from slides and notes, so they can be short or fragmentary.\n"
    "- Use only the excerpts. Do not add facts from outside them.\n"
    "- If the excerpts cover the question only partly, answer with what they say "
    "and note what is missing.\n"
    "- Say you don't know only if the excerpts are unrelated to the question.\n"
    "- When you use an excerpt, cite it like (file, p.N).\n\n"
    "Excerpts:\n{context}\n\n"
    "Question: {question}"
)
answer_chain = prompt | llm | StrOutputParser()


def ask(question, scope=None, history=None):
    history = history or []
    search_q = question
    if history:
        past = "\n".join(f"User: {q}\nAI: {a}" for q, a in history[-config.HISTORY_TURNS:])
        search_q = llm.invoke(
            f"Chat history:\n{past}\n\n"
            "Rewrite this new question so it makes sense on its own. "
            f"Return only the question.\n\nNew question: {question}"
        ).content.strip()

    variants, ranked = retrieve(search_q, scope)
    if not ranked:
        return {"answer": "I don't know. Nothing matching is indexed yet.",
                "searched_for": variants, "sources": []}

    context = "\n\n".join(
        f"[{Path(d.metadata['source']).name}, p.{d.metadata.get('page', 0) + 1}]\n{d.page_content}"
        for d in build_context(ranked)
    )
    answer = answer_chain.invoke({"context": context, "question": search_q})
    sources = [
        {"file": Path(doc.metadata["source"]).name,
         "page": doc.metadata.get("page", 0) + 1,
         "score": round(float(score), 2),
         "text": doc.page_content[:300]}
        for score, doc in ranked
    ]
    return {"answer": answer, "searched_for": variants, "sources": sources}


# ---------- flashcards and quiz ----------
def pick_rich(docs):
    rich = [d for d in docs if len(d.page_content) >= config.MIN_STUDY_CHARS]
    return rich if len(rich) >= 3 else docs


def get_material(scope, topic):
    where = {"source": scope} if scope else None
    if topic.strip():
        docs = store.similarity_search(topic.strip(), k=config.STUDY_CHUNKS * 2, filter=where)
    else:
        data = store.get(where=where, include=["documents", "metadatas"])
        docs = [Document(page_content=t, metadata=m)
                for t, m in zip(data["documents"], data["metadatas"])]
        random.shuffle(docs)
    docs = pick_rich(docs)[: config.STUDY_CHUNKS]
    return "\n\n".join(
        f"[{Path(d.metadata['source']).name} p.{d.metadata.get('page', 0) + 1}]\n{d.page_content}"
        for d in docs
    )


def generate_json(task, material):
    if not material.strip():
        return []
    for _ in range(2):
        text = creative_llm.invoke(f"{task}\n\nLecture excerpts:\n{material}").content
        match = re.search(r"\[.*\]", text, re.S)
        if match:
            try:
                items = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            if isinstance(items, list) and items:
                return items
    return []


def make_cards(scope, topic, n):
    items = generate_json(
        f"Create {n} flashcards for studying from the lecture excerpts below. Test key "
        "concepts, definitions and reasoning. Answers must be short (1-3 sentences). "
        "Use only the excerpts. Return ONLY a JSON list like "
        '[{"q": "question", "a": "answer"}] with no other text.',
        get_material(scope, topic),
    )
    return [{"q": x["q"], "a": x["a"]} for x in items
            if isinstance(x, dict) and isinstance(x.get("q"), str) and isinstance(x.get("a"), str)]


def make_quiz(scope, topic, n):
    items = generate_json(
        f"Create {n} multiple-choice questions from the lecture excerpts below. Each has "
        "exactly 4 options and one correct answer. Use only the excerpts. In the "
        "explanation, mention the [file p.N] tag it came from. Return ONLY a JSON list like "
        '[{"question": "...", "options": ["...", "...", "...", "..."], '
        '"answer": 0, "explanation": "..."}] where answer is the index (0-3) of the '
        "correct option. No other text.",
        get_material(scope, topic),
    )
    quiz = []
    for x in items:
        if not (isinstance(x, dict) and isinstance(x.get("question"), str)
                and isinstance(x.get("options"), list) and len(x["options"]) >= 2):
            continue
        answer = x.get("answer")
        if isinstance(answer, str):
            answer = "ABCD".find(answer.strip()[:1].upper()) if answer.strip() else -1
        if isinstance(answer, int) and 0 <= answer < len(x["options"]):
            quiz.append({"question": x["question"],
                         "options": [str(o) for o in x["options"]],
                         "answer": answer,
                         "explanation": str(x.get("explanation", ""))})
    return quiz


# ---------- summary ----------
STYLES = {
    "Short overview": "Write a short overview (about 150 words) of this lecture.",
    "Detailed notes": "Write well-organized study notes with headings and bullet points.",
    "Key concepts": "List the key concepts as bullets in the form 'Term: definition'.",
}


def summarize(source, style):
    data = store.get(where={"source": source}, include=["documents", "metadatas"])
    ordered = sorted(zip(data["documents"], data["metadatas"]), key=lambda p: p[1].get("page", 0))
    text = "\n".join(t for t, _ in ordered if t.strip())
    if not text.strip():
        return ""
    size = config.SUMMARY_BATCH_CHARS
    notes = [
        llm.invoke("Summarize the key points of this part of a lecture as concise bullet "
                   "points. Keep important terms, formulas and definitions.\n\n" + text[i:i + size]).content
        for i in range(0, len(text), size)
    ]
    return llm.invoke(STYLES[style] + "\n\nNotes from the lecture:\n" + "\n\n".join(notes)).content
