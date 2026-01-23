"""
Thumbnail generation worker using libvips.
Processes uploaded photos and generates multiple thumbnail sizes.
"""
from celery import Task
from app.celery_app import celery_app
try:
    import pyvips
    HAS_PYVIPS = True
except (ImportError, OSError):
    HAS_PYVIPS = False
    print("Warning: libvips not found, falling back to PIL for thumbnails.")

import hashlib
import imagehash
from PIL import Image, ImageOps
from typing import Tuple
import os
import tempfile
from datetime import datetime

from app.services.b2_service import b2_service


# ... (CallbackTask and process_upload remain same, just ensure global HAS_PYVIPS is used if needed, or function abstraction handles it)

def generate_thumbnail(
    input_path: str,
    output_path: str,
    size: int,
    format: str = "webp"
) -> Tuple[int, int]:
    """
    Generate thumbnail using libvips (preferred) or PIL (fallback).
    """
    if HAS_PYVIPS:
        try:
            return _generate_thumbnail_vips(input_path, output_path, size, format)
        except Exception as e:
            print(f"VIPS failed ({e}), falling back to PIL")
            # Fallthrough to PIL
            pass
            
    return _generate_thumbnail_pil(input_path, output_path, size, format)


def _generate_thumbnail_vips(input_path, output_path, size, format) -> Tuple[int, int]:
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


def _generate_thumbnail_pil(input_path, output_path, size, format) -> Tuple[int, int]:
    with Image.open(input_path) as img:
        # Auto-rotate
        img = ImageOps.exif_transpose(img)
        
        # Calculate new size maintaining aspect ratio
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Save
        if format == 'webp':
            img.save(output_path, 'WEBP', quality=85)
        elif format == 'avif':
            # PIL might not support AVIF out of box without plugin, fallback to webp or jpeg?
            # Safe fallback: jpeg if avif requested but not supported? 
            # Assuming env has support or we just try. 
            # If fail, use WEBP?
            try:
                img.save(output_path, 'AVIF', quality=75, speed=6)
            except:
                print("AVIF not supported by PIL, saving as WEBP")
                img.save(output_path, 'WEBP', quality=85)
        else: # jpeg usually
            # Convert RGBA to RGB for JPEG
            if img.mode in ('RGBA', 'LA'):
                background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                background.paste(img, img.split()[-1])
                img = background.convert('RGB')
            img.save(output_path, 'JPEG', quality=90, optimize=True)
            
        return img.size


class CallbackTask(Task):
    """Base task with database session."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        print(f"Task {task_id} failed: {exc}")


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
def process_upload(self, upload_id: str, photo_id: str):
    """
    Process uploaded photo: generate thumbnails, computed hashes, extract EXIF.
    """
    import asyncio
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.photo import Photo
    import os
    
    async def _process():
        async with AsyncSessionLocal() as db:
            # 1. Fetch photo to get user_id and filename
            result = await db.execute(select(Photo).where(Photo.photo_id == photo_id))
            photo = result.scalar_one_or_none()
            
            if not photo:
                print(f"Photo {photo_id} not found")
                return
            
            try:
                # 2. Download original from B2
                # Construct B2 key (assuming specific structure from upload.py)
                # "uploads/{user_id}/{upload_id}/original/{filename}" if via presigned
                # OR "uploads/{user_id}/{photo_id}/original/{filename}" if via direct?
                # upload.py direct uses photo_id. presigned uses upload_id.
                
                # Check which one to use.
                # If upload_id is provided and legit UUID, it might be the folder. 
                # But direct upload uses photo_id as the folder ID in B2 too?
                # Direct: b2_key = f"uploads/{current_user.user_id}/{photo.photo_id}/original/{file.filename}"
                # Presigned: b2_key = f"uploads/{user_id}/{upload_id}/original/{filename}"
                
                # We need to know which path.
                # If upload_id == photo_id (as string), then it matches direct upload logic?
                # But upload.py passes `upload_id` (a new uuid) for presigned.
                
                # Let's try both or standardize?
                # We can't change the B2 key now easily for existing uploads without moving.
                # But for NEW uploads:
                # If we use presign, the file is at `.../{upload_id}/...`.
                # We want it at `.../{photo_id}/...` for long term consistency?
                # Or just update the DB with the actual B2 path? NO, DB doesn't store B2 path, it constructs it dynamically in `photos.py` using `photo_id`.
                
                # CRITICAL ISSUE:
                # `photos.py` download/thumbnail logic constructs key as:
                # `f"uploads/{current_user.user_id}/{photo.photo_id}/original/{photo.filename}"`
                
                # But `presign` logic in `upload.py` puts it at:
                # `f"uploads/{user_id}/{upload_id}/original/{filename}"`
                
                # So if `upload_id` != `photo_id`, `photos.py` will FAIL to find the file!
                # We MUST move the file from `upload_id` path to `photo_id` path IN THIS WORKER.
                # This is a critical discovery.
                
                # Step 2a: Move object if needed (for presigned uploads)
                # If upload_id != photo_id:
                #    Copy from upload_id path to photo_id path.
                #    Delete original? 
                
                # Actually, `b2_service` doesn't have copy exposed yet.
                # But we can download and upload.
                
                source_key = f"uploads/{photo.user_id}/{upload_id}/original/{photo.filename}"
                dest_key = f"uploads/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
                
                # Download
                print(f"Downloading from {source_key}")
                original_bytes = b2_service.download_file_bytes(source_key)
                
                # If we moved it effectively by downloading, we should re-upload to key expected by API if they differ
                if upload_id != str(photo.photo_id):
                    print(f"Moving to {dest_key}")
                    b2_service.get_bucket().upload_bytes(
                        data_bytes=original_bytes,
                        file_name=dest_key,
                        content_type=photo.mime_type
                    )
                    # Ideally delete the old one, but let's leave it for cleanup or implicit
                    # b2_service.delete_file_version? We don't have ID.
                
                # 3. Generate Thumbnails
                # Save temp file
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(original_bytes)
                    tmp_path = tmp.name
                
                sizes = [256, 512, 1024]
                for size in sizes:
                    thumb_key = f"uploads/{photo.user_id}/{photo.photo_id}/thumbnails/thumb_{size}.jpg"
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as thumb_tmp:
                        thumb_path = thumb_tmp.name
                        
                    generate_thumbnail(tmp_path, thumb_path, size, format='jpeg')
                    
                    # Upload
                    with open(thumb_path, 'rb') as f:
                        thumb_bytes = f.read()
                        
                    b2_service.get_bucket().upload_bytes(
                        data_bytes=thumb_bytes,
                        file_name=thumb_key,
                        content_type='image/jpeg'
                    )
                    os.unlink(thumb_path)
                    
                # 4. Compute Hashes & Metadata
                sha256 = compute_sha256(tmp_path)
                phash = compute_perceptual_hash(tmp_path)
                size_bytes = len(original_bytes)
                
                # 4a. Attempt to extract date from filename if taken_at is missing (e.g., WhatsApp)
                # WhatsApp format: "WhatsApp Image 2025-10-25 at 16.37.02.jpeg"
                import re
                filename_date = None
                
                # Regex for WhatsApp matching: YYYY-MM-DD at HH.MM.SS
                # Also matches "IMG-20251025-WA0001" style if needed, but let's target the specific one seen
                wa_pattern = re.search(r"(\d{4}-\d{2}-\d{2}) at (\d{2}\.\d{2}\.\d{2})", photo.filename)
                if wa_pattern:
                    try:
                        date_str = wa_pattern.group(1)
                        time_str = wa_pattern.group(2).replace('.', ':')
                        filename_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                        print(f"Extracted date from filename: {filename_date}")
                    except ValueError:
                        pass
                
                # Fallback: YYYYMMDD_HHMMSS or IMG_YYYYMMDD_HHMMSS
                if not filename_date:
                    compact_pattern = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", photo.filename)
                    if compact_pattern:
                        try:
                            # Verify years are reasonable (e.g. 2000-2099)
                            if 2000 <= int(compact_pattern.group(1)) <= 2099:
                                filename_date = datetime(
                                    int(compact_pattern.group(1)),
                                    int(compact_pattern.group(2)),
                                    int(compact_pattern.group(3)),
                                    int(compact_pattern.group(4)),
                                    int(compact_pattern.group(5)),
                                    int(compact_pattern.group(6))
                                )
                                print(f"Extracted date from compact filename: {filename_date}")
                        except ValueError:
                            pass

                # Update DB
                photo.size_bytes = size_bytes
                photo.sha256 = sha256
                # Ensure phash is stored as signed 64-bit integer for Postgres BIGINT
                if phash >= 2**63:
                    phash -= 2**64
                photo.phash = phash
                
                # Update taken_at if found in filename and not already set (EXIF would set it if implemented, but we aren't doing full EXIF here yet)
                # TODO: Implement full EXIF extraction. For now, filename fallback is good.
                if filename_date:
                    photo.taken_at = filename_date
                
                photo.processed_at = datetime.utcnow()
                
                await db.commit()
                
                os.unlink(tmp_path)
                print(f"Successfully processed photo {photo_id}")
                
            except Exception as e:
                print(f"Error processing photo {photo_id}: {e}")
                raise e

    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Should not happen in synchronous celery worker, but just in case
        return loop.create_task(_process())
    else:
        return asyncio.run(_process())

    return {
        "status": "success",
        "photo_id": photo_id
    }


# Function body replaced by previous block, ensuring we don't duplicate. 
# Actually, the previous tool call might have replaced imports but mismatched the TargetContent if I wasn't careful.
# Let's check what I replaced. 
# I replaced from line 7 to START of generate_thumbnail?
# The TargetContent in previous call was "import pyvips... from app.services.b2_service import b2_service".
# That covers imports. 
# Now I need to delete the OLD generate_thumbnail function implementation because I redefined it in the previous block?
# NO, I defined `generate_thumbnail` in the previous REPLACEMENT string, but I replaced the IMPORTS block.
# So now `generate_thumbnail` is defined TWICE?
# Yes, likely. I need to remove the old implementation.



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
