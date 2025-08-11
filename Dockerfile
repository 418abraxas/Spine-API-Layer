FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONUNBUFFERED=1
# Render sets PORT; uvicorn honors 8080 default but we’ll bind 0.0.0.0 in start cmd via render.yaml/native
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
