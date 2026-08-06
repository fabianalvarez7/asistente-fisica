FROM python:3.11-slim

# HF Spaces requires UID 1000 (non-root). All files must be owned by this user.
RUN useradd -m -u 1000 user

WORKDIR /app

# System deps: libgomp1 for torch CPU OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (cached layer). CPU-only torch via PyTorch's CPU index
# avoids downloading ~2 GB of CUDA binaries the free CPU tier cannot use.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download the embedding model at build time. HF Spaces' free tier
# caps GitHub LFS at 100 MB per file, and multilingual-e5-small is
# 448 MB, so we cannot track the model in git. Downloading here bakes
# it into the image layer; no network round-trip on first request.
# Uses scripts/preparar_indice_hf.py so the dev and deploy paths share
# a single source of truth.
COPY scripts/preparar_indice_hf.py ./scripts/preparar_indice_hf.py
RUN mkdir -p /app/rag/index/hf-model && \
    HF_HOME=/app/rag/index/hf-model \
    SENTENCE_TRANSFORMERS_HOME=/app/rag/index/hf-model \
    python scripts/preparar_indice_hf.py && \
    chown -R user:user /app/rag/index/hf-model

# Pre-download marker-pdf/surya models at build time (~3.5 GB). Same
# pattern as the embedding model: bake once, no network round-trip on
# first /chat request after Space sleep. The cache is NOT committed to
# git (too large); it lives in the image layer.
RUN mkdir -p /app/rag/index/marker-models && \
    MODEL_CACHE_DIR=/app/rag/index/marker-models \
    TORCH_DEVICE_MODEL=cpu \
    python -c "from marker.models import create_model_dict; create_model_dict()" && \
    chown -R user:user /app/rag/index/marker-models

# Copy app code and the pre-baked ChromaDB index. The HF model and marker
# models are excluded from the build context via .dockerignore (already
# downloaded above, so we never overwrite with stale local copies).
COPY --chown=user . .

# Non-sensitive runtime config. Sensitive vars (GROQ_API_KEY) are injected as
# HF Space Secrets at runtime — NOT set here.
ENV CHROMA_PERSIST_DIR=./rag/index/chroma
ENV HF_HOME=./rag/index/hf-model
ENV SENTENCE_TRANSFORMERS_HOME=./rag/index/hf-model
ENV MODEL_CACHE_DIR=./rag/index/marker-models
ENV TORCH_DEVICE_MODEL=cpu
ENV OMP_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false
ENV LLM_MODEL=llama-3.3-70b-versatile

# SQLite history dir: .dockerignore excludes data/ from the build context, so
# the dir is missing in the image. /app itself is owned by root with 0755
# (Docker WORKDIR default), so the runtime UID 1000 cannot create /app/data
# at boot. Pre-create it here with the right owner. The DB file itself is
# ephemeral (HF Spaces wipes disk on sleep) — accepted per AGENTS.md §7.12.
RUN mkdir -p /app/data && chown user:user /app/data

USER user

# Port 7860 is HF Spaces' default app_port. Must match README YAML.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
