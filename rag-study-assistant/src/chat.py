from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src import config
from src.models import llm
from src.retrieval import retrieve

prompt = ChatPromptTemplate.from_template(
    "You are a helpful assistant. Answer the question using only the context below. "
    "If the context does not contain the answer, say you don't know.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)
answer_chain = prompt | llm | StrOutputParser()


def standalone_question(question, history):
    past = "\n".join(f"User: {q}\nAI: {a}" for q, a in history[-config.HISTORY_TURNS:])
    return llm.invoke(
        f"Chat history:\n{past}\n\n"
        "Rewrite this new question so it makes sense on its own. "
        f"Return only the question.\n\nNew question: {question}"
    ).content.strip()


def ask(question, scope=None, history=None):
    history = history or []
    search_q = standalone_question(question, history) if history else question
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
