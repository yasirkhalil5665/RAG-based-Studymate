import json
import random
import re
from pathlib import Path

from langchain_core.documents import Document

from src import config
from src.models import creative_llm
from src.vectorstore import store


def get_material(scope=None, topic=""):
    where = {"source": scope} if scope else None
    if topic.strip():
        docs = store.similarity_search(topic.strip(), k=config.MATERIAL_CHUNKS, filter=where)
    else:
        data = store.get(where=where, include=["documents", "metadatas"])
        docs = [Document(page_content=t, metadata=m)
                for t, m in zip(data["documents"], data["metadatas"])]
        random.shuffle(docs)
        docs = docs[: config.MATERIAL_CHUNKS]
    text = ""
    for d in docs:
        tag = f"[{Path(d.metadata['source']).name} p.{d.metadata.get('page', 0) + 1}]"
        piece = f"{tag}\n{d.page_content}\n\n"
        if len(text) + len(piece) > config.MATERIAL_MAX_CHARS:
            break
        text += piece
    return text


def parse_json_list(text):
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def generate_items(instructions, material):
    for _ in range(2):
        raw = creative_llm.invoke(instructions + "\n\nLecture excerpts:\n" + material).content
        items = parse_json_list(raw)
        if items:
            return items
    return []


def make_cards(scope=None, topic="", n=10):
    items = generate_items(
        f"Create {n} flashcards for studying from the lecture excerpts below. Test key "
        "concepts, definitions and reasoning. Answers must be short (1-3 sentences). "
        "Use only the excerpts. Return ONLY a JSON list like "
        '[{"q": "question", "a": "answer"}] with no other text.',
        get_material(scope, topic),
    )
    return [{"q": x["q"], "a": x["a"]} for x in items
            if isinstance(x, dict) and isinstance(x.get("q"), str) and isinstance(x.get("a"), str)]


def clean_answer_index(value, options):
    if isinstance(value, str) and value.strip()[:1].upper() in {"A", "B", "C", "D"}:
        value = "ABCD".index(value.strip()[:1].upper())
    return value if isinstance(value, int) and 0 <= value < len(options) else None


def make_quiz(scope=None, topic="", n=5):
    items = generate_items(
        f"Create {n} multiple-choice questions from the lecture excerpts below. Each has "
        "exactly 4 options and one correct answer. Use only the excerpts. In the "
        "explanation, mention the [file p.N] tag it came from. Return ONLY a JSON list like "
        '[{"question": "...", "options": ["...", "...", "...", "..."], '
        '"answer": 0, "explanation": "..."}] where answer is the index (0-3) of the '
        "correct option. No other text.",
        get_material(scope, topic),
    )
    questions = []
    for x in items:
        if not (isinstance(x, dict) and isinstance(x.get("question"), str)
                and isinstance(x.get("options"), list) and len(x["options"]) >= 2):
            continue
        answer = clean_answer_index(x.get("answer"), x["options"])
        if answer is not None:
            questions.append({"question": x["question"],
                              "options": [str(o) for o in x["options"]],
                              "answer": answer,
                              "explanation": str(x.get("explanation", ""))})
    return questions
