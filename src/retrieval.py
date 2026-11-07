from src import config
from src.models import llm, reranker
from src.vectorstore import store


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
