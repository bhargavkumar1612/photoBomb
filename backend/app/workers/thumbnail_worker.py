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
try:
    import pillow_avif
except ImportError:
    pass
from typing import Tuple, Optional
import os
import tempfile
from datetime import datetime
from app.core.config import settings
import asyncio
import gc
import time
import logging
from contextlib import contextmanager
from sqlalchemy import select
from app.models.photo import Photo
from app.core.database import AsyncSessionLocal
import numpy as np

# Conditional imports for animal detection
if settings.ANIMAL_DETECTION_ENABLED:
    from app.services.animal_detector import detect_animals, get_animal_embedding
    from app.models.animal import AnimalDetection

# Pipeline tracking imports
from app.services.pipeline_service import (
    update_pipeline_task_status,
    update_pipeline_task_complete,
    update_pipeline_task_error,
    update_pipeline_progress
)

logger = logging.getLogger(__name__)


# Global cache for models to avoid reloading on every task
_model_cache = {
    "face_recognition": None,
    "face_recognition_error": None
}


@contextmanager
def timer(name: str):
    """Context manager to time operations and return metrics"""
    start = time.perf_counter()
    metrics = {}
    yield metrics
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    metrics[f'{name}_time_ms'] = elapsed_ms
    logger.info(f"⏱️  {name}: {elapsed_ms}ms")


def get_face_recognition():
    """Lazy load face_recognition library"""
    if _model_cache["face_recognition"]:
        return _model_cache["face_recognition"]
    
    if _model_cache["face_recognition_error"]:
        raise _model_cache["face_recognition_error"]
        
    try:
        import face_recognition
        _model_cache["face_recognition"] = face_recognition
        return face_recognition
    except ImportError as e:
        _model_cache["face_recognition_error"] = e
        raise e







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
        try:
            img = ImageOps.exif_transpose(img)
        except (Exception, ZeroDivisionError, TypeError) as e:
            print(f"Warning: Failed to auto-rotate image {input_path} due to corrupt EXIF: {e}")
            # Continue with original image
            pass
        
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


def save_crop(storage, image_path, box, dest_key, padding=0.2):
    """
    Crop area from image and upload to storage.
    box: (top, right, bottom, left) for consistency with face_recognition
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            top, right, bottom, left = box
            
            # Ensure within bounds
            top = max(0, top)
            right = min(width, right)
            bottom = min(height, bottom)
            left = max(0, left)
            
            # Padding
            w = right - left
            h = bottom - top
            top = max(0, int(top - h * padding))
            bottom = min(height, int(bottom + h * padding))
            left = max(0, int(left - w * padding))
            right = min(width, int(right + w * padding))
            
            crop = img.crop((left, top, right, bottom))
            crop.thumbnail((512, 512)) # Higher res for crops
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                crop_path = tmp.name
                
            crop.save(crop_path, "JPEG", quality=90)
            
            with open(crop_path, 'rb') as f:
                storage.upload_bytes(f.read(), dest_key, content_type='image/jpeg')
            
            os.unlink(crop_path)
            return True
    except Exception as e:
        print(f"Error saving crop to {dest_key}: {e}")
        return False


class CallbackTask(Task):
    """Base task with database session."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        print(f"Task {task_id} failed: {exc}")


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
def process_photo_initial(self, upload_id: str, photo_id: str, pipeline_id: Optional[str] = None):
    """
    Step 1: Process uploaded photo: generate thumbnails, computed hashes, extract EXIF.
    Optionally tracks progress in a pipeline.
    
    Args:
        upload_id: Upload batch ID
        photo_id: Photo UUID
        pipeline_id: Optional pipeline UUID for progress tracking
    """
    task_start = time.perf_counter()
    metrics = {}
    
    async def _process():
        # Update pipeline task status if tracking
        if pipeline_id:
            await update_pipeline_task_status(
                pipeline_id, photo_id,
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            logger.info(f"📦 Pipeline {pipeline_id} | Photo {photo_id} | Starting initial processing")
        
        async with AsyncSessionLocal() as db:
            # 1. Fetch photo to get user_id and filename
            # Use unique execution to avoid connection pool issues
            result = await db.execute(select(Photo).where(Photo.photo_id == photo_id))
            photo = result.scalar_one_or_none()
            
            if not photo:
                print(f"Photo {photo_id} not found")
                if pipeline_id:
                    await update_pipeline_task_error(
                        pipeline_id, photo_id,
                        error_message="Photo not found in database",
                        error_type="not_found"
                    )
                    await update_pipeline_progress(pipeline_id)
                return
            
            try:
                # 2. Download original
                # Use storage service factory
                # Use storage service factory
                from app.services.storage_factory import get_storage_service
                print(f"Worker using provider: {photo.storage_provider} for photo {photo.photo_id}")
                storage = get_storage_service(photo.storage_provider)
                
                source_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{upload_id}/original/{photo.filename}"
                dest_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
                
                try:
                    # Download with timing
                    print(f"Downloading from {source_key}")
                    with timer('download') as t:
                        try:
                            original_bytes = storage.download_file_bytes(source_key)
                        except Exception as e:
                            print(f"Source key {source_key} failed: {e}. Trying destination {dest_key}...")
                            original_bytes = storage.download_file_bytes(dest_key)
                            current_upload_id = str(photo.photo_id)
                        metrics.update(t)

                except Exception as e:
                    print(f"Critical: Could not find original file for photo {photo_id}: {e}")
                    if pipeline_id:
                        await update_pipeline_task_error(
                            pipeline_id, photo_id,
                            error_message=f"Failed to download original: {str(e)}",
                            error_type="download_failed"
                        )
                        await update_pipeline_progress(pipeline_id)
                    return

                # If we moved it effectively by downloading, we should re-upload to key expected by API if they differ
                # Compare the original argument 'upload_id' with the photo id
                if 'current_upload_id' in locals() and current_upload_id == str(photo.photo_id):
                    # It was found at destination, so no move needed.
                    pass
                elif upload_id != str(photo.photo_id):
                    print(f"Moving to {dest_key}")
                    try:
                         storage.upload_bytes(
                            data_bytes=original_bytes,
                            key=dest_key,
                            content_type=photo.mime_type
                        )
                    except Exception as e:
                        print(f"Failed to copy to dest: {e}")
                        pass # Continue if we have the bytes
                
                # 3. Generate Thumbnails with timing
                with timer('thumbnail_generation') as t:
                    sizes = [256, 512, 1024]
                    for size in sizes:
                        thumb_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/thumbnails/thumb_{size}.jpg"
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as thumb_tmp:
                            thumb_path = thumb_tmp.name
                            
                        generate_thumbnail(tmp_path, thumb_path, size, format='jpeg')
                        
                        # Upload
                        with open(thumb_path, 'rb') as f:
                            thumb_bytes = f.read()
                            
                        storage.upload_bytes(
                            data=thumb_bytes,
                            key=thumb_key,
                            content_type='image/jpeg'
                        )
                        os.unlink(thumb_path)
                    metrics.update(t)
                    
                # 4. Compute Hashes & Metadata
                sha256 = compute_sha256(tmp_path)
                phash = compute_perceptual_hash(tmp_path)
                size_bytes = len(original_bytes)

                # 4a. Extract EXIF Data (Taken At, GPS)
                import piexif
                from PIL.ExifTags import TAGS, GPSTAGS
                
                exif_data = {}
                gps_data = {}
                
                try:
                    # Load image to read info
                    with Image.open(tmp_path) as img:
                        info = img._getexif()
                        if info:
                            for tag, value in info.items():
                                decoded = TAGS.get(tag, tag)
                                if decoded == "GPSInfo":
                                    for t in value:
                                        sub_decoded = GPSTAGS.get(t, t)
                                        gps_data[sub_decoded] = value[t]
                                else:
                                    exif_data[decoded] = value
                except Exception as e:
                    print(f"Error extracting EXIF: {e}")

                # Parse Taken At
                taken_at = None
                if "DateTimeOriginal" in exif_data:
                    try:
                        taken_at = datetime.strptime(exif_data["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass
                
                # If not in EXIF, check filename (WhatsApp etc) - already implemented below but we can prioritize EXIF
                if taken_at:
                    photo.taken_at = taken_at
                
                # Parse GPS
                def convert_to_degrees(value):
                    d, m, s = value
                    return d + (m / 60.0) + (s / 3600.0)

                if "GPSLatitude" in gps_data and "GPSLongitude" in gps_data:
                    try:
                        lat = convert_to_degrees(gps_data["GPSLatitude"])
                        lng = convert_to_degrees(gps_data["GPSLongitude"])
                        
                        if gps_data.get("GPSLatitudeRef") == "S":
                            lat = -lat
                        if gps_data.get("GPSLongitudeRef") == "W":
                            lng = -lng
                            
                        photo.gps_lat = lat
                        photo.gps_lng = lng
                        
                        # Reverse Geocode
                        import reverse_geocoder as rg
                        results = rg.search((lat, lng))
                        if results:
                            # e.g., output: [{'lat': '...', 'lon': '...', 'name': 'City Name', 'admin1': 'State', 'cc': 'Country Code'}]
                            city = results[0].get('name')
                            state = results[0].get('admin1')
                            country = results[0].get('cc')
                            location_parts = [p for p in [city, state, country] if p]
                            photo.location_name = ", ".join(location_parts)
                            print(f"Location found: {photo.location_name}")
                            
                    except Exception as e:
                        print(f"Error parsing GPS: {e}")
                    except Exception as e:
                        print(f"Error parsing GPS: {e}")

                # Update DB with timing
                with timer('db_write') as t:
                    photo.size_bytes = size_bytes
                    photo.sha256 = sha256
                    photo.phash = phash
                    photo.exif_data = exif_data
                    photo.taken_at = taken_at
                    photo.gps_lat = gps_lat
                    photo.gps_lng = gps_lng
                    
                    # ... filename fallback logic would go here if needed again, or relies on previous updates
                    # Re-adding filename fallback logic within the block
                    if not photo.taken_at:
                        import re
                        wa_pattern = re.search(r"(\d{4}-\d{2}-\d{2}) at (\d{2}\.\d{2}\.\d{2})", photo.filename)
                        if wa_pattern:
                            try:
                                date_str = wa_pattern.group(1)
                                time_str = wa_pattern.group(2).replace('.', ':')
                                photo.taken_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                pass
                        
                        if not photo.taken_at:
                            compact_pattern = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", photo.filename)
                            if compact_pattern:
                                try:
                                    if 2000 <= int(compact_pattern.group(1)) <= 2099:
                                        photo.taken_at = datetime(
                                            int(compact_pattern.group(1)),
                                            int(compact_pattern.group(2)),
                                            int(compact_pattern.group(3)),
                                            int(compact_pattern.group(4)),
                                            int(compact_pattern.group(5)),
                                            int(compact_pattern.group(6))
                                        )
                                except ValueError:
                                    pass

                    await db.commit()
                    metrics.update(t)
                
                os.unlink(tmp_path)
                print(f"Successfully finished initial processing for {photo_id}")
                
                # Calculate total time and update pipeline
                total_time_ms = int((time.perf_counter() - task_start) * 1000)
                
                if pipeline_id:
                    await update_pipeline_task_complete(
                        pipeline_id, photo_id,
                        status='completed',
                        total_time_ms=total_time_ms,
                        **metrics
                    )
                    await update_pipeline_progress(pipeline_id)
                    logger.info(f"✅ Photo {photo_id} completed in {total_time_ms}ms")
                
                # Manual Trigger Only (to prevent OOM)
                # celery_app.send_task('app.workers.thumbnail_worker.process_photo_analysis', args=[upload_id, photo_id])

            except Exception as e:
                print(f"Error processing photo {photo_id}: {e}")
                if pipeline_id:
                    await update_pipeline_task_error(
                        pipeline_id, photo_id,
                        error_message=str(e),
                        error_type="processing_error"
                    )
                    await update_pipeline_progress(pipeline_id)
                # Log error in DB?
            finally:
                if 'tmp_path' in locals() and tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                # Force release of memory
                import gc
                gc.collect()
                # raise e # Don't raise if we handled it via pipeline error tracking? 
                # Actually we should probably raise so Celery knows it failed, 
                # BUT if we marked it as failed in pipeline, maybe we don't want Celery retry loop?
                # User config says max_retries=3. 
                # Let's keep raising e to allow retries, but pipeline will show 'failed' temporarily until retry succeeds?
                # Better: only mark failed in pipeline on LAST retry.
                # For now, let's just mark it failed.
                raise e

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(_process())


@celery_app.task(bind=True, base=CallbackTask, max_retries=2)
def process_photo_analysis(self, upload_id: str, photo_id: str, pipeline_id: Optional[str] = None):
    """
    Step 2: AI Analysis (Face, Objects, Animals, Text).
    Runs separately to avoid OOM.
    Optionally tracks progress in a pipeline.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    task_start = time.perf_counter()
    metrics = {}
    
    async def _analyze():
        # Update pipeline task status if tracking
        if pipeline_id:
            await update_pipeline_task_status(
                pipeline_id, photo_id,
                status='running',
                celery_task_id=self.request.id,
                started_at=datetime.utcnow()
            )
            logger.info(f"📦 Pipeline {pipeline_id} | Photo {photo_id} | Starting analysis")

        tmp_path = None
        try:
            # ========================================
            # STEP 1: Quick fetch of photo metadata
            # ========================================
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Photo).where(Photo.photo_id == photo_id))
                photo = result.scalar_one_or_none()
                
                if not photo:
                    logger.warning(f"Photo {photo_id} not found for analysis - task will be skipped")
                    print(f"⚠️  Photo {photo_id} not found for analysis", flush=True)
                    if pipeline_id:
                        await update_pipeline_task_error(
                            pipeline_id, photo_id,
                            error_message="Photo not found for analysis",
                            error_type="not_found"
                        )
                        await update_pipeline_progress(pipeline_id)
                    return
                
                # Store metadata we need for processing
                user_id = photo.user_id
                filename = photo.filename
                storage_provider = photo.storage_provider
            # Session closed here - no connection held during AI processing
            
            # ========================================
            # STEP 2: Download and AI Processing (No DB Connection)
            # ========================================
            tmp_path = None
            
            # Data structures to collect results
            face_results = []
            animal_results = []
            tag_results = []
            
            try:
                from app.services.storage_factory import get_storage_service
                storage = get_storage_service(storage_provider)
                
                # Determine key (it should be at dest_key now)
                dest_key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/{photo_id}/original/{filename}"
                
                try:
                    # Download
                    original_bytes = storage.download_file_bytes(dest_key)
                except Exception as e:
                    logger.error(f"Analysis: Could not download {dest_key}: {e}")
                    print(f"❌ Analysis: Could not download {dest_key}: {e}", flush=True)
                    return
    
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(original_bytes)
                    tmp_path = tmp.name
    
                # Free up bytes memory
                del original_bytes
    
                # 4c. Face Recognition
                with timer('face_detection') as t:
                    try:
                        face_recognition = get_face_recognition()
                        from app.models.person import Face
                        
                        # Convert PIL Image to RGB and then to numpy array
                        with Image.open(tmp_path) as img:
                            # Ensure RGB
                            if img.mode != 'RGB':
                                rgb_img = img.convert('RGB')
                            else:
                                rgb_img = img
                            
                            np_image = np.array(rgb_img)
                            
                        print(f"🔍 Detecting faces in {filename}...", flush=True)
                        # Detect faces (HOG-based model is faster, cnn is more accurate but requires GPU)
                        face_locations = face_recognition.face_locations(np_image, model="hog")
                        print(f"✅ Found {len(face_locations)} faces", flush=True)
                        logger.info(f"Found {len(face_locations)} faces in photo {photo_id}")
                        
                        if face_locations:
                            face_encodings = face_recognition.face_encodings(np_image, face_locations)
                            
                            for idx, (location, encoding) in enumerate(zip(face_locations, face_encodings)):
                                top, right, bottom, left = location
                                
                                # Save facial crop immediately (before tmp_path is deleted)
                                # Use temporary face_id based on index since we don't have DB id yet
                                temp_face_key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/faces/temp_{photo_id}_{idx}.jpg"
                                save_crop(storage, tmp_path, (top, right, bottom, left), temp_face_key, padding=0.4)
                                
                                # Store face data for later DB insert
                                face_data = {
                                    'photo_id': photo_id,
                                    'encoding': encoding.tolist(),
                                    'location_top': top,
                                    'location_right': right,
                                    'location_bottom': bottom,
                                    'location_left': left,
                                    'temp_crop_key': temp_face_key  # Store temp key for renaming later
                                }
                                face_results.append(face_data)
                                
                    except ImportError as e:
                        logger.error(f"Face recognition libraries not installed: {e}")
                        print("❌ Face recognition libraries not found/installed. Skipping.", flush=True)
                    except Exception as e:
                        logger.exception(f"Error in face recognition for photo {photo_id}: {e}")
                        print(f"💥 Error in face recognition: {e}", flush=True)
                    
                    metrics.update(t)
    
    
                # 4d. Animal Detection (DETR + CLIP) - Only if enabled
                with timer('animal_detection') as t:
                    if settings.ANIMAL_DETECTION_ENABLED:
                        try:
                            print(f"Detecting animals in {filename}...")
                            detections = detect_animals(tmp_path, threshold=0.7)
                            print(f"Found {len(detections)} animals")
                            
                            for idx, det in enumerate(detections):
                                # DETR box: [xmin, ymin, xmax, ymax]
                                # Convert to (top, right, bottom, left) for save_crop
                                xmin, ymin, xmax, ymax = det['box']
                                box = (int(ymin), int(xmax), int(ymax), int(xmin))
                                
                                embedding = get_animal_embedding(tmp_path, det['box'])
                                
                                # Save animal crop immediately
                                temp_animal_key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/animals/crops/temp_{photo_id}_{idx}.jpg"
                                save_crop(storage, tmp_path, box, temp_animal_key, padding=0.1)
                                
                                # Store animal data
                                animal_data = {
                                    'photo_id': photo_id,
                                    'label': det['label'],
                                    'confidence': det['confidence'],
                                    'embedding': embedding,
                                    'location_top': box[0],
                                    'location_right': box[1],
                                    'location_bottom': box[2],
                                    'location_left': box[3],
                                    'temp_crop_key': temp_animal_key
                                }
                                animal_results.append(animal_data)
                                
                                # Also prepare tag data for animals
                                animal_tag_name = det['label'].lower().replace(" ", "")
                                tag_results.append({
                                    'name': animal_tag_name,
                                    'category': 'animals',
                                    'confidence': det['confidence']
                                })
                        except Exception as e:
                            print(f"Error in animal detection: {e}")
                    else:
                        print(f"⏭️  Skipping animal detection (ANIMAL_DETECTION_ENABLED=False)")
                    metrics.update(t)
    
    
                # 4e. Object & Scene Detection (CLIP)
                with timer('classification') as t:
                    from app.services.classifier import classify_image
                    from app.services.document_classifier import classify_document
        
                    print(f"Classifying scene in {filename}...")
                    
                    # Call service
                    classification_results = classify_image(tmp_path, threshold=0.4)
                    
                    for res in classification_results:
                        tag_results.append({
                            'name': res['label'],
                            'category': res['category'],
                            'confidence': res['score']
                        })
        
                    # 2. Granular Document Classification (Second Pass)
                    if any(res['category'] == 'documents' for res in classification_results):
                        with timer('document_detection') as t_doc:
                            print(f"Document detected, performing granular classification...")
                            doc_results = classify_document(tmp_path, threshold=0.3)
                            
                            for res in doc_results:
                                # Add as hashtag-style tag
                                tag_name = res['label'].lower().replace(" ", "")
                                tag_results.append({
                                    'name': tag_name,
                                    'category': 'documents',
                                    'confidence': res['score']
                                })
                        metrics.update(t_doc)
                    metrics.update(t)
    
                # 4f. Text Detection (OCR)
                with timer('ocr') as t:
                    try:
                        import pytesseract
                        print(f"Running OCR on {filename}...")
                        text = pytesseract.image_to_string(tmp_path)
                        # Simple tokenization: splits by whitespace, keeps alphanumeric > 3 chars
                        words = set(w.lower() for w in text.split() if len(w) > 3 and w.isalnum())
                        
                        if words:
                            print(f"Found text: {list(words)[:10]}...")
                            
                        for word in words:
                            tag_results.append({
                                'name': word,
                                'category': 'text',
                                'confidence': 1.0
                            })
                                
                    except ImportError:
                        print("pytesseract not installed")
                    except Exception as e:
                        # e.g. Tesseract binary not found
                        print(f"OCR warning: {e}")
                    metrics.update(t)
    
                print(f"Classification complete.")
                print(f"Analysis/Classification complete for {filename}")
                
            except Exception as e:
                print(f"Error analyzing photo {photo_id}: {e}")
                raise e
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
            # ========================================
            # STEP 3: Batch write all results to database
            # ========================================
            async with AsyncSessionLocal() as db:
                try:
                    from app.models.person import Face
                    from app.models.tag import Tag, PhotoTag
                    
                    # Re-fetch photo for update
                    result = await db.execute(select(Photo).where(Photo.photo_id == photo_id))
                    photo = result.scalar_one_or_none()
                    
                    if not photo:
                        logger.warning(f"Photo {photo_id} disappeared during processing")
                        return
                    
                    # Write all faces and rename crops
                    for face_data in face_results:
                        temp_crop_key = face_data.pop('temp_crop_key')  # Remove before creating Face object
                        new_face = Face(**face_data)
                        db.add(new_face)
                        await db.flush()  # Get face_id
                        
                        # Rename facial crop from temp to final location
                        final_face_key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/faces/{new_face.face_id}.jpg"
                        try:
                            # Download temp and re-upload to final location
                            crop_bytes = storage.download_file_bytes(temp_crop_key)
                            storage.upload_bytes(crop_bytes, final_face_key, content_type='image/jpeg')
                            # Delete temp
                            storage.delete_file(temp_crop_key)
                        except Exception as e:
                            logger.warning(f"Failed to rename face crop: {e}")
                    
                    # Write all animals and rename crops
                    for animal_data in animal_results:
                        temp_crop_key = animal_data.pop('temp_crop_key')
                        new_det = AnimalDetection(**animal_data)
                        db.add(new_det)
                        await db.flush()
                        
                        # Rename animal crop from temp to final location
                        final_animal_key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/animals/crops/{new_det.detection_id}.jpg"
                        try:
                            crop_bytes = storage.download_file_bytes(temp_crop_key)
                            storage.upload_bytes(crop_bytes, final_animal_key, content_type='image/jpeg')
                            storage.delete_file(temp_crop_key)
                        except Exception as e:
                            logger.warning(f"Failed to rename animal crop: {e}")
                    
                    # Write all tags
                    # Group by tag name to avoid duplicates
                    unique_tags = {}
                    for tag_data in tag_results:
                        tag_name = tag_data['name']
                        if tag_name not in unique_tags:
                            unique_tags[tag_name] = tag_data
                        else:
                            # Keep higher confidence
                            if tag_data['confidence'] > unique_tags[tag_name]['confidence']:
                                unique_tags[tag_name] = tag_data
                    
                    for tag_name, tag_data in unique_tags.items():
                        # Check existing tag
                        result = await db.execute(select(Tag).where(Tag.name == tag_name))
                        existing_tag = result.scalar_one_or_none()
                        
                        tag_id = None
                        if not existing_tag:
                            try:
                                new_tag = Tag(name=tag_name, category=tag_data['category'])
                                db.add(new_tag)
                                await db.flush()
                                tag_id = new_tag.tag_id
                            except Exception:
                                # Race condition likely
                                await db.rollback()
                                result = await db.execute(select(Tag).where(Tag.name == tag_name))
                                existing_tag = result.scalar_one()
                                tag_id = existing_tag.tag_id
                        else:
                            tag_id = existing_tag.tag_id
                            # Update category if needed
                            if existing_tag.category == "general" and tag_data['category'] != "general":
                                existing_tag.category = tag_data['category']
                                db.add(existing_tag)
                            elif not existing_tag.category and tag_data['category']:
                                existing_tag.category = tag_data['category']
                                db.add(existing_tag)
    
                        # Create PhotoTag
                        link_res = await db.execute(select(PhotoTag).where(
                            PhotoTag.photo_id == photo_id,
                            PhotoTag.tag_id == tag_id
                        ))
                        if not link_res.scalar_one_or_none():
                            pt = PhotoTag(photo_id=photo_id, tag_id=tag_id, confidence=tag_data['confidence'], source='ai')
                            db.add(pt)
    
                    # Mark as fully processed
                    photo.processed_at = datetime.utcnow()
                    
                    # Update DB with timing
                    with timer('db_write') as t:
                        await db.commit()
                        metrics.update(t)
                    
                    total_time_ms = int((time.perf_counter() - task_start) * 1000)
                    
                    # Collect counts for metrics
                    counts = {
                        'faces_detected': len(face_results),
                        'animals_detected': len(animal_results),
                        'tags_created': len(unique_tags) if 'unique_tags' in locals() else len(tag_results),
                        'text_words_extracted': len([t for t in tag_results if t.get('category') == 'text'])
                    }
                    metrics.update(counts)
                    
                    if pipeline_id:
                        await update_pipeline_task_complete(
                            pipeline_id, photo_id,
                            status='completed',
                            total_time_ms=total_time_ms,
                            **metrics
                        )
                        await update_pipeline_progress(pipeline_id)
                        logger.info(f"✅ Pipeline {pipeline_id} | Photo {photo_id} | Analysis completed in {total_time_ms}ms")
                    else:
                        print(f"✅ Successfully saved all analysis results for {filename} in {total_time_ms}ms")
                    
                except Exception as e:
                    await db.rollback()
                    logger.exception(f"Error saving analysis results for photo {photo_id}: {e}")
                    print(f"❌ Error saving results: {e}", flush=True)
                    raise e
    
        except Exception as e:
            logger.error(f"Error analyzing photo {photo_id}: {e}")
            print(f"Error analyzing photo {photo_id}: {e}")
            if pipeline_id:
                await update_pipeline_task_error(
                    pipeline_id, photo_id,
                    error_message=str(e),
                    error_type="analysis_error"
                )
                await update_pipeline_progress(pipeline_id)
            raise e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            gc.collect()
    
    
    # Create a fresh event loop for this task to avoid "Event loop is closed" errors
    # Celery workers may reuse processes, and the event loop might be closed from a previous task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        # There's a running loop, but it might be closed. Create a new one to be safe.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_analyze())
    finally:
        # Clean up the loop after task completion
        try:
            loop.close()
        except Exception:
            pass  # Ignore errors when closing the loop




# Legacy Task Alias (for draining old queue messages)
process_upload = process_photo_initial

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