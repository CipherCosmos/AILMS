FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/user-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and install their dependencies
COPY shared/ ./shared/
RUN pip install --no-cache-dir -r shared/requirements.txt

# Copy service code
COPY services/user-service/ ./services/user-service/


# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the service
WORKDIR /app/services/user-service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]