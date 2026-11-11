FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/config.py src/config.py
RUN python -c "from src import config; from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer(config.EMBED_MODEL); CrossEncoder(config.RERANK_MODEL)"

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
