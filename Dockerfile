FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV RUNS_DIR=/app/outputs
EXPOSE 8000
CMD ["sh", "-c", "uvicorn rfp_pipeline.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
