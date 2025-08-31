FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/assessment-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and install their dependencies
COPY shared/ ./shared/
RUN pip install --no-cache-dir -r shared/requirements.txt

# Copy service code
COPY services/assessment-service/ ./services/assessment-service/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Run the service
CMD ["python", "services/assessment-service/main.py"]