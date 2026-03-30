FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY agent_server.py .

ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT:-8000}

CMD uvicorn agent_server:app --host 0.0.0.0 --port ${PORT:-8000}
