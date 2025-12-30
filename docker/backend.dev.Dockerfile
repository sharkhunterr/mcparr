# Development Dockerfile for FastAPI backend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install development tools
RUN pip install --no-cache-dir \
    black \
    ruff \
    mypy \
    pytest \
    pytest-asyncio \
    pytest-cov \
    ipython

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 8001

# Run with hot reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]