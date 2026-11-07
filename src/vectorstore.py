from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config
from src.models import embeddings

store = Chroma(persist_directory=config.CHROMA_DIR, embedding_function=embeddings)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
)
