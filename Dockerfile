# Multi-stage build for Feedny - Optimized for Railway Serverless

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies including Arabic fonts for wordcloud
RUN apt-get update && apt-get install -y \
    libfreetype6 \
    libpng16-16 \
    fonts-noto-core \
    fonts-dejavu-core \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Set Python optimizations for serverless
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=1

# Copy application code
COPY app/ ./app/
COPY .env.example .env

# Create directory for database
RUN mkdir -p /app/data && \
    chmod 755 /app/data

# Expose port
EXPOSE 8000

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run with workers optimized for serverless (single worker, faster startup)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

