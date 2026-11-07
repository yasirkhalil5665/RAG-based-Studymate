from langchain_community.document_loaders import PyPDFLoader

from src import config
from src.models import llm
from src.vectorstore import store

STYLES = {
    "Short overview": "Write a short overview (about 150 words) of this lecture.",
    "Detailed notes": "Write well-organized study notes with headings and bullet points.",
    "Key concepts": "List the key concepts as bullets in the form 'Term: definition'.",
}


def page_texts(source):
    try:
        pages = PyPDFLoader(source).load()
        return [p.page_content for p in pages if p.page_content.strip()]
    except Exception:
        return store.get(where={"source": source}, include=["documents"])["documents"]


def group_text(parts, limit):
    groups, current = [], ""
    for part in parts:
        if current and len(current) + len(part) > limit:
            groups.append(current)
            current = ""
        current += part + "\n"
    if current:
        groups.append(current)
    return groups


def summarize(source, style="Short overview"):
    parts = [
        llm.invoke("Summarize the key points of these lecture pages as concise bullet points. "
                   "Keep important terms, formulas and definitions.\n\n" + group).content
        for group in group_text(page_texts(source), config.SUMMARY_GROUP_CHARS)
    ]
    combined = "\n\n".join(parts)
    while len(combined) > config.SUMMARY_MAX_COMBINED:
        parts = [llm.invoke("Condense these notes, keeping key terms:\n\n" + group).content
                 for group in group_text(parts, config.SUMMARY_MAX_COMBINED // 2)]
        combined = "\n\n".join(parts)
    return llm.invoke(STYLES[style] + "\n\nNotes from the lecture:\n" + combined).content
