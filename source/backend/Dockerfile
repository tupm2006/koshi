FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code. See .dockerignore — .env, data/ and .venv/ must never
# be copied into the image.
COPY . .

# The runtime owns this directory; in production it is a mounted volume.
RUN mkdir -p /app/data

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
