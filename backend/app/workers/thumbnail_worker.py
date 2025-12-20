"""
Thumbnail generation worker using libvips.
Processes uploaded photos and generates multiple thumbnail sizes.
"""
from celery import Task
from app.celery_app import celery_app
import pyvips
import hashlib
import imagehash
from PIL import Image
from typing import Tuple
import os
import tempfile

from app.services.b2_service import b2_service


class CallbackTask(Task):
    """Base task with database session."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        print(f"Task {task_id} failed: {exc}")


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
def process_upload(self, upload_id: str, photo_id: str):
    """
    Process uploaded photo: generate thumbnails, compute hashes, extract EXIF.
    
    Args:
        upload_id: Upload session ID
        photo_id: Photo record ID
    
    Steps:
        1. Download original from B2
        2. Generate thumbnails (256px, 512px, 1024px) in WebP/AVIF/JPEG
        3. Compute SHA256 and pHash
        4. Extract EXIF data
        5. Upload thumbnails to B2
        6. Update database
    """
    try:
        print(f"Processing upload {upload_id} for photo {photo_id}")
        
        # TODO: Fetch upload session from database to get B2 key
        # TODO: Download original from B2
        # TODO: Generate thumbnails
        # TODO: Compute hashes
        # TODO: Extract EXIF
        # TODO: Upload thumbnails to B2
        # TODO: Update photo record in database
        
        # Placeholder implementation
        print(f"Upload {upload_id} processed successfully")
        
        return {
            "status": "success",
            "photo_id": photo_id,
            "thumbnails_generated": 9  # 3 sizes × 3 formats
        }
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


def generate_thumbnail(
    input_path: str,
    output_path: str,
    size: int,
    format: str = "webp"
) -> Tuple[int, int]:
    """
    Generate thumbnail using libvips.
    
    Args:
        input_path: Path to source image
        output_path: Path to save thumbnail
        size: Longest edge size in pixels
        format: Output format (webp, avif, jpeg)
    
    Returns:
        Tuple of (width, height) of generated thumbnail
    """
    # Load image
    image = pyvips.Image.new_from_file(input_path, access='sequential')
    
    # Auto-rotate based on EXIF orientation
    image = image.autorot()
    
    # Calculate scale factor
    scale = size / max(image.width, image.height)
    if scale < 1:
        image = image.resize(scale, kernel='lanczos3')
    
    # Format-specific options
    if format == 'webp':
        image.write_to_file(output_path, Q=85, strip=True)
    elif format == 'avif':
        image.write_to_file(output_path, Q=75, speed=6, strip=True)
    else:  # jpeg
        image.write_to_file(output_path, Q=90, optimize_coding=True, strip=False)
    
    return (image.width, image.height)


def compute_perceptual_hash(image_path: str) -> int:
    """
    Compute perceptual hash (pHash) for duplicate detection.
    
    Args:
        image_path: Path to image file
    
    Returns:
        64-bit integer hash
    """
    img = Image.open(image_path)
    phash = imagehash.phash(img, hash_size=8)
    return int(str(phash), 16)


def compute_sha256(file_path: str) -> str:
    """
    Compute SHA256 hash of file.
    
    Args:
        file_path: Path to file
    
    Returns:
        Hex-encoded SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks for large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
