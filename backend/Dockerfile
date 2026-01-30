# Use PyTorch CPU runtime as base to save ~2GB of download/install time
FROM pytorch/pytorch:2.2.1-cpu-runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Limit compilation threads to prevent OOM
ENV CMAKE_BUILD_PARALLEL_LEVEL=4
ENV MAKEFLAGS="-j 4"

# Install system dependencies
# libvips-dev: Image processing
# libpq-dev: PostgreSQL driver compilation
# build-essential: Compiler tools
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libffi-dev \
    libvips-dev \
    libglib2.0-dev \
    libexpat1-dev \
    libgirepository1.0-dev \
    libpq-dev \
    postgresql-client \
    curl \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# 1. Install heavy dependencies (cached layer)
# These are already partly in the base image (torch, torchvision)
# uv will skip what's already installed
COPY requirements-base.txt .
RUN uv pip install --system --no-cache-dir -r requirements-base.txt

# 2. Install application dependencies (frequently changing layer)
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Make scripts executable
RUN chmod +x scripts/start_prod.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command
CMD ["./scripts/start_prod.sh"]