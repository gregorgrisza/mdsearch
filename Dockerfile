FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install  --no-cache-dir --upgrade pip
RUN pip install  --no-cache-dir -r requirements.txt

COPY . /app


EXPOSE 8000
EXPOSE 5678

CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", \
      "-m", "uvicorn", "app_qdrant:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["uvicorn", "app_qdrant:app", "--host", "0.0.0.0", "--port", "8000"]