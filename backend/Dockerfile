# Use your custom pre-baked base image!
# This image already contains torch, torchvision, dlib, face_recognition, and libvips.
FROM bhargavkumar1612/photobomb-base:latest

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install light application dependencies
# Note: Since the base image already has the heavy ones, this is very fast.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x scripts/start_prod.sh

# Expose port
EXPOSE 8000

# Default command
CMD ["./scripts/start_prod.sh"]