# Use your custom pre-baked base image from Docker Hub
# This contains python:3.11-slim + torch (cpu) + dlib + face_recognition + libvips
FROM bhargavkumar1612/photobomb-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install light application dependencies only
# We skip requirements-base.txt because those libs are already in the base image
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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