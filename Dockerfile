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

# Copy app code and pre-baked artifacts. --chown ensures UID 1000 owns everything.
COPY --chown=user . .

# Non-sensitive runtime config. Sensitive vars (GROQ_API_KEY) are injected as
# HF Space Secrets at runtime — NOT set here.
ENV CHROMA_PERSIST_DIR=./rag/index/chroma
ENV HF_HOME=./rag/index/hf-model
ENV SENTENCE_TRANSFORMERS_HOME=./rag/index/hf-model
ENV OMP_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false
ENV LLM_MODEL=llama-3.3-70b-versatile

USER user

# Port 7860 is HF Spaces' default app_port. Must match README YAML.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
