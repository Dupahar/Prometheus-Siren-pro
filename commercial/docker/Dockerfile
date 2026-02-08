FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src /app/src
COPY services /app/services
COPY dashboard /app/dashboard

# Environment variables
ENV PYTHONPATH=/app

# Default command (overridden by compose)
CMD ["python"]
