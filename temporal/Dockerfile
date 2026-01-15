# Temporal Worker Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependencies
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy worker code
COPY ./workflows ./workflows
COPY ./activities ./activities
COPY ./worker.py ./worker.py

# Create non-root user
RUN useradd -m -u 1000 worker && chown -R worker:worker /app
USER worker

# Run worker
CMD ["python", "worker.py"]
