FROM python:3.11.9-slim

WORKDIR /app

# System deps for wheels that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Ensure data dir for Chroma (RAG)
RUN mkdir -p /app/data/chroma

# Run
ENV PORT=8000 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
