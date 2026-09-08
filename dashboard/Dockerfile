FROM python:3.11-slim

# Space runs as UID 1000 by convention; keep the same user as the chat app.
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Install dependencies from the repo root.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the application code.
COPY app/ /app/app/
COPY dashboard/ /app/dashboard/
COPY rag/ /app/rag/

# Streamlit needs a writable directory for caches and temporary files.
RUN mkdir -p /app/.streamlit /app/.cache && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
