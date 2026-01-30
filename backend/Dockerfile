FROM python:3.11-slim-bookworm

# Set environment variables
# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr (faster logs)
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# libvips-dev: Image processing
# libpq-dev: PostgreSQL driver compilation
# build-essential: Compiler tools
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libffi-dev \
    python3-dev \
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

# Limit compilation threads to prevent OOM
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
ENV MAKEFLAGS="-j 1"

# Install Python dependencies
# 1. Install heavy dependencies (cached layer)
COPY requirements-base.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-base.txt

# 2. Install application dependencies (frequently changing layer)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

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