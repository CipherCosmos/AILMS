FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and install their dependencies
COPY shared/ ./shared/
RUN pip install --no-cache-dir -r shared/requirements.txt

# Copy service code
COPY services/api-gateway/ ./services/api-gateway/


# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
WORKDIR /app/services/api-gateway
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]