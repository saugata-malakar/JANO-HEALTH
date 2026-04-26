# Hugging Face Spaces uses port 7860 by default.
# Build context for this image is the repo root; we copy from resume-ai-system/backend.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf \
    SENTENCE_TRANSFORMERS_HOME=/tmp/st

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY resume-ai-system/backend/requirements.txt .
RUN pip install -r requirements.txt

# Pre-download the embedding model so cold starts don't fetch on first request.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY resume-ai-system/backend/app ./app

# HF Spaces convention: listen on 7860, allow any origin so the Vercel frontend can call us.
ENV ALLOWED_ORIGINS="*"
ENV DEV_BYPASS_AUTH=true

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
