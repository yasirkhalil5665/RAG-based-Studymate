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
from sentence_transformers import CrossEncoder

from src import config

embeddings = HuggingFaceEmbeddings(model_name=config.EMBED_MODEL)
llm = ChatOllama(model=config.LLM_MODEL, temperature=0)
creative_llm = ChatOllama(model=config.LLM_MODEL, temperature=config.CREATIVE_TEMPERATURE)
reranker = CrossEncoder(config.RERANK_MODEL)
store = Chroma(persist_directory=config.CHROMA_DIR, embedding_function=embeddings)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
)
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


def add_pdf(path):
    source = source_of(path)
    pages = PyPDFLoader(str(path)).load()
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
        print(f"Indexed {pdf.name}" if count else f"Skipped {pdf.name}: no readable text (scanned PDF?)")


def remove_source(source):
    ids = store.get(where={"source": source})["ids"]
    if ids:
        store.delete(ids=ids)
    path = config.BASE_DIR / source
    if path.parent == config.LIB_DIR:
        path.unlink(missing_ok=True)


# ---------- retrieval ----------
def expand(question):
    out = llm.invoke(
        "Fix the spelling of this question, then write 2 alternative phrasings "
        "using synonyms. Return one per line, nothing else.\n\nQuestion: " + question
    ).content
    return [line.strip() for line in out.split("\n") if line.strip()][:3] or [question]


def rerank(question, docs):
    scores = reranker.predict([(question, d.page_content) for d in docs])
    ranked = sorted(zip(scores, docs), key=lambda pair: pair[0], reverse=True)
    return ranked[: config.TOP_K]


def retrieve(question, scope=None):
    variants = expand(question)
    where = {"source": scope} if scope else None
    candidates = {}
    for variant in variants:
        for doc in store.similarity_search(variant, k=config.SEARCH_K, filter=where):
            candidates[doc.page_content] = doc
    ranked = rerank(variants[0], list(candidates.values())) if candidates else []
    return variants, ranked


# ---------- chat ----------
prompt = ChatPromptTemplate.from_template(
    "You are a helpful assistant. Answer the question using only the context below. "
    "If the context does not contain the answer, say you don't know.\n\n"
    "Context:\n{context}\n\n"
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

    context = "\n\n".join(doc.page_content for _, doc in ranked)
    answer = answer_chain.invoke({"context": context, "question": variants[0]})
    sources = [
        {"file": Path(doc.metadata["source"]).name,
         "page": doc.metadata.get("page", 0) + 1,
         "score": round(float(score), 2),
         "text": doc.page_content[:300]}
        for score, doc in ranked
    ]
    return {"answer": answer, "searched_for": variants, "sources": sources}


# ---------- flashcards and quiz ----------
def get_material(scope, topic):
    where = {"source": scope} if scope else None
    if topic.strip():
        docs = store.similarity_search(topic.strip(), k=config.STUDY_CHUNKS, filter=where)
    else:
        data = store.get(where=where, include=["documents", "metadatas"])
        docs = [Document(page_content=t, metadata=m)
                for t, m in zip(data["documents"], data["metadatas"])]
        random.shuffle(docs)
        docs = docs[: config.STUDY_CHUNKS]
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
    try:
        pages = [p.page_content for p in PyPDFLoader(str(config.BASE_DIR / source)).load()]
    except Exception:
        pages = store.get(where={"source": source}, include=["documents"])["documents"]
    text = "\n".join(p for p in pages if p.strip())
    if not text.strip():
        return ""
    size = config.SUMMARY_BATCH_CHARS
    notes = [
        llm.invoke("Summarize the key points of this part of a lecture as concise bullet "
                   "points. Keep important terms, formulas and definitions.\n\n" + text[i:i + size]).content
        for i in range(0, len(text), size)
    ]
    return llm.invoke(STYLES[style] + "\n\nNotes from the lecture:\n" + "\n\n".join(notes)).content

