FROM python:3.11-slim

# Install system dependencies (libvips for image processing)
RUN apt-get update && apt-get install -y \
    libvips-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
# Make start script executable
RUN chmod +x scripts/start_prod.sh

# Default command uses production start script
CMD ["./scripts/start_prod.sh"]
