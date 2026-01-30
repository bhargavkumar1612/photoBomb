import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env before importing app modules
load_dotenv()
import tempfile
import logging
from sqlalchemy import select
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.tag import Tag, PhotoTag
from app.models.person import Face # Import Face model
from app.core.config import settings
from app.services.classifier import classify_image
from app.services.storage_factory import get_storage_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print(f"\\n{'='*50}")
print(f"CONFIGURATION CHECK:")
print(f"DB_SCHEMA:        {settings.DB_SCHEMA}")
print(f"STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")
if settings.STORAGE_PROVIDER == 's3':
    print(f"BUCKET_NAME:      {settings.S3_BUCKET_NAME}")
else:
    print(f"BUCKET_NAME:      {settings.B2_BUCKET_NAME}")
print(f"{'='*50}\\n")

# Try importing face_recognition
try:
    import face_recognition
    import cv2
    import numpy as np
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition or cv2 not installed. Face detection will be skipped.")

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not installed. OCR will be skipped.")

async def process_photo(db, photo):
    logger.info(f"Processing photo {photo.filename} (ID: {photo.photo_id})")
    
    tmp_path = None
    try:
        # 1. Download Photo to Temp
        storage = get_storage_service(photo.storage_provider)
        source_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
        
        try:
            file_bytes = storage.download_file_bytes(source_key)
        except Exception as e:
            # Fallback to destination key (if file was already processed/moved)
            dest_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
            try:
                # logger.info(f"Source failed, trying dest: {dest_key}")
                file_bytes = storage.download_file_bytes(dest_key)
            except Exception as e2:
                logger.warning(f"Failed to find photo {photo.filename}: {e} / {e2}")
                return

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # 1b. Regenerate Thumbnails
        try:
            # Fix AVIF support (plugin might not auto-register)
            try:
                import pillow_avif
            except ImportError:
                pass
                
            from app.workers.thumbnail_worker import generate_thumbnail
            
            sizes = [256, 512, 1024]
            for size in sizes:
                thumb_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/thumbnails/thumb_{size}.jpg"
                
                # OPTIMIZATION: Skip if already exists (Removed for full rescan request)
                # if storage.file_exists(thumb_key):
                #     logger.debug(f"Thumb {size} for {photo.photo_id} already exists, skipping.")
                #     continue
                pass
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as thumb_tmp:
                    thumb_path = thumb_tmp.name
                
                try:
                    # Generate
                    generate_thumbnail(tmp_path, thumb_path, size, format='jpeg')
                    
                    # Upload
                    with open(thumb_path, 'rb') as f:
                        thumb_data = f.read()
                        
                    storage.upload_bytes(data_bytes=thumb_data, key=thumb_key, content_type='image/jpeg')
                    logger.info(f"Generated thumb_{size}")
                except Exception as e:
                    logger.warning(f"Failed to generate/upload thumb_{size}: {e}")
                finally:
                    if os.path.exists(thumb_path):
                        os.unlink(thumb_path)
        except ImportError:
            logger.warning("Could not import generate_thumbnail. Skipping thumbnail generation.")
        except Exception as e:
            logger.error(f"Thumbnail generation error: {e}")

        # 2. Re-Classify (CLIP)
        try:
            results = classify_image(tmp_path, threshold=0.4)
            
            for res in results:
                label = res['label']
                score = res['score']
                category = res['category']
                
                # Find or Create Tag
                from app.services.classifier import determine_category
                
                # Re-determine category to ensure it matches current logic (e.g. people)
                category = determine_category(label)
                
                result = await db.execute(select(Tag).where(Tag.name == label))
                existing_tag = result.scalar_one_or_none()
                
                tag_id = None
                if not existing_tag:
                    new_tag = Tag(name=label, category=category)
                    db.add(new_tag)
                    await db.flush()
                    tag_id = new_tag.tag_id
                else:
                    tag_id = existing_tag.tag_id
                    # Force update category if it's general or incorrect
                    if existing_tag.category != category:
                        existing_tag.category = category
                        db.add(existing_tag)
                
                # Link PhotoTag
                link_res = await db.execute(select(PhotoTag).where(
                    PhotoTag.photo_id == photo.photo_id,
                    PhotoTag.tag_id == tag_id
                ))
                if not link_res.scalar_one_or_none():
                    pt = PhotoTag(photo_id=photo.photo_id, tag_id=tag_id, confidence=score)
                    db.add(pt)
                    logger.info(f"Added tag: {label} ({category})")
        except Exception as e:
            logger.warning(f"Classification failed for {photo.filename}: {e}")

        # 3. Fix Location (if missing)
        if not photo.location_name and photo.gps_lat and photo.gps_lng:
            try:
                import reverse_geocoder as rg
                results = rg.search((photo.gps_lat, photo.gps_lng))
                if results:
                    city = results[0].get('name')
                    state = results[0].get('admin1')
                    country = results[0].get('cc')
                    parts = [p for p in [city, state, country] if p]
                    photo.location_name = ", ".join(parts)
                    db.add(photo)
                    logger.info(f"Updated location: {photo.location_name}")
            except ImportError:
                pass
            except Exception as e:
                logger.error(f"Location error: {e}")

        # 4. Face Recognition (New)
        if FACE_RECOGNITION_AVAILABLE:
            # Check if faces already exist to avoid duplicates
            existing_faces_res = await db.execute(select(Face).where(Face.photo_id == photo.photo_id))
            if not existing_faces_res.scalars().first():
                try:
                    image = face_recognition.load_image_file(tmp_path)
                    # Use HOG model for speed (CNN is better but requires CUDA/slow on CPU)
                    face_locations = face_recognition.face_locations(image)
                    
                    if face_locations:
                        logger.info(f"Found {len(face_locations)} faces.")
                        face_encodings = face_recognition.face_encodings(image, face_locations)
                        
                        for location, encoding in zip(face_locations, face_encodings):
                            top, right, bottom, left = location
                            # Store encoding as list of floats
                            encoding_list = encoding.tolist()
                            
                            new_face = Face(
                                photo_id=photo.photo_id,
                                encoding=encoding.tolist(),
                                location_top=top,
                                location_right=right,
                                location_bottom=bottom,
                                location_left=left
                            )
                            db.add(new_face)
                            await db.flush() # Get ID

                            # Save facial crop
                            from app.workers.thumbnail_worker import save_crop
                            face_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/faces/{new_face.face_id}.jpg"
                            save_crop(storage, tmp_path, (top, right, bottom, left), face_key, padding=0.4)

                        logger.info(f"Added {len(face_encodings)} face encodings.")
                    else:
                        logger.info("No faces found.")
                except Exception as e:
                    logger.error(f"Face recognition error: {e}")

        if OCR_AVAILABLE:
             try:
                print(f"Running OCR on {photo.filename}...")
                text = pytesseract.image_to_string(tmp_path)
                # Simple tokenization: splits by whitespace, keeps alphanumeric > 3 chars
                words = set(w.lower() for w in text.split() if len(w) > 3 and w.isalnum())
                
                if words:
                    print(f"Found text: {list(words)[:10]}...")
                    
                for word in words:
                    # Check/Create tag
                    tag_name = word
                    
                    # Optimization: Check if tag exists (cache this lookup?)
                    stmt = await db.execute(select(Tag).where(Tag.name == tag_name))
                    existing_tag = stmt.scalar_one_or_none()
                    
                    tag_id = None
                    if not existing_tag:
                        try:
                            new_tag = Tag(name=tag_name, category="text")
                            db.add(new_tag)
                            await db.flush()
                            tag_id = new_tag.tag_id
                        except Exception:
                            await db.rollback()
                            stmt = await db.execute(select(Tag).where(Tag.name == tag_name))
                            existing_tag = stmt.scalar_one()
                            tag_id = existing_tag.tag_id
                    else:
                        tag_id = existing_tag.tag_id
                        if not existing_tag.category: # Don't overwrite if it was "general" or "documents"
                            existing_tag.category = "text"
                            db.add(existing_tag)

                    # Link
                    link_res = await db.execute(select(PhotoTag).where(
                        PhotoTag.photo_id == photo.photo_id,
                        PhotoTag.tag_id == tag_id
                    ))
                    if not link_res.scalar_one_or_none():
                        pt = PhotoTag(photo_id=photo.photo_id, tag_id=tag_id, confidence=1.0) # 1.0 confidence for OCR
                        db.add(pt)
            
             except Exception as e:
                logger.error(f"OCR error: {e}")

        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing {photo.photo_id}: {e}")
        await db.rollback()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Photo))
        photos = result.scalars().all()
        logger.info(f"Found {len(photos)} photos to rescan.")
        
        for photo in photos:
            await process_photo(db, photo)
            
    logger.info("Rescan complete.")

if __name__ == "__main__":
    asyncio.run(main())
