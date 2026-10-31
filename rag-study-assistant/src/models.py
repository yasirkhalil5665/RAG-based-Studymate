from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from sentence_transformers import CrossEncoder

from src import config

embeddings = HuggingFaceEmbeddings(model_name=config.EMBED_MODEL)
llm = ChatOllama(model=config.LLM_MODEL, temperature=0)
creative_llm = ChatOllama(model=config.LLM_MODEL, temperature=config.GEN_TEMPERATURE)
reranker = CrossEncoder(config.RERANK_MODEL)
