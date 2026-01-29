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
                # 2. Download original
                # Use storage service factory
                # Use storage service factory
                from app.services.storage_factory import get_storage_service
                print(f"Worker using provider: {photo.storage_provider} for photo {photo.photo_id}")
                storage = get_storage_service(photo.storage_provider)
                
                source_key = f"uploads/{photo.user_id}/{upload_id}/original/{photo.filename}"
                dest_key = f"uploads/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
                
                # Download
                print(f"Downloading from {source_key}")
                original_bytes = storage.download_file_bytes(source_key)
                
                # If we moved it effectively by downloading, we should re-upload to key expected by API if they differ
                if upload_id != str(photo.photo_id):
                    print(f"Moving to {dest_key}")
                    storage.upload_bytes(
                        data_bytes=original_bytes,
                        key=dest_key,
                        content_type=photo.mime_type
                    )
                    # Ideally delete the old one
                
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
                        
                    storage.upload_bytes(
                        data_bytes=thumb_bytes,
                        key=thumb_key,
                        content_type='image/jpeg'
                    )
                    os.unlink(thumb_path)
                    
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

                # 4c. Face Recognition
                try:
                    import face_recognition
                    import numpy as np
                    from app.models.person import Face
                    
                    # Convert PIL Image to RGB and then to numpy array
                    with Image.open(tmp_path) as img:
                        # Ensure RGB
                        if img.mode != 'RGB':
                            rgb_img = img.convert('RGB')
                        else:
                            rgb_img = img
                        
                        # Resize for faster processing if image is huge (optional, but recommended for speed)
                        # face_recognition works best on moderate sizes, but for accuracy on high-res, full size is better but slower.
                        # Let's keep full size for now or cap at 1600px max dimension?
                        # For now, just use original.
                        np_image = np.array(rgb_img)
                        
                    print(f"Detecting faces in {photo.filename}...")
                    # Detect faces (HOG-based model is faster, cnn is more accurate but requires GPU)
                    face_locations = face_recognition.face_locations(np_image, model="hog")
                    print(f"Found {len(face_locations)} faces")
                    
                    if face_locations:
                        face_encodings = face_recognition.face_encodings(np_image, face_locations)
                        
                        for location, encoding in zip(face_locations, face_encodings):
                            top, right, bottom, left = location
                            
                            new_face = Face(
                                photo_id=photo.photo_id,
                                encoding=encoding.tolist(),  # Store as list, pgvector will handle it
                                location_top=top,
                                location_right=right,
                                location_bottom=bottom,
                                location_left=left
                            )
                            db.add(new_face)
                            # Note: We are NOT assigning person_id yet. That happens in clustering step.
                            
                except ImportError:
                    print("Face recognition libraries not found/installed. Skipping.")
                except Exception as e:
                    print(f"Error in face recognition: {e}")

                # 4d. Object & Scene Detection (CLIP)
                try:
                    from transformers import pipeline
                    from app.models.tag import Tag, PhotoTag
                    from app.core.database import AsyncSessionLocal
                    from sqlalchemy import select

                    # Labels
                    candidate_labels = [
                        "animal", "dog", "cat", "bird", "wildlife",
                        "document", "receipt", "invoice", "id card", "paper",
                        "nature", "beach", "mountain", "forest", "sunset", "sky",
                        "city", "architecture", "street", "building",
                        "food", "drink", "meal",
                        "vehicle", "car", "bicycle", "plane",
                        "screenshot", "text", "diagram"
                    ]
                    
                    print(f"Classifying scene in {photo.filename}...")
                    
                    # Use 'zero-shot-image-classification'
                    # Model: 'openai/clip-vit-base-patch32'
                    classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
                    
                    # Predict
                    results = classifier(tmp_path, candidate_labels=candidate_labels)
                    
                    # Filter and save
                    for res in results:
                        label = res['label']
                        score = res['score']
                        
                        if score > 0.2: # Threshold
                            # Check existing tag
                            result = await db.execute(select(Tag).where(Tag.name == label))
                            existing_tag = result.scalar_one_or_none()
                            
                            tag_id = None
                            if not existing_tag:
                                # Determine category
                                category = "general"
                                if label in ["dog", "cat", "bird", "animal", "wildlife"]:
                                    category = "animal"
                                elif label in ["document", "receipt", "invoice", "id card", "paper", "text", "diagram"]:
                                    category = "document"
                                elif label in ["nature", "beach", "mountain", "forest", "sunset", "sky", "city", "architecture", "street", "building"]:
                                    category = "place"
                                
                                try:
                                    new_tag = Tag(name=label, category=category)
                                    db.add(new_tag)
                                    await db.flush()
                                    tag_id = new_tag.tag_id
                                except Exception: 
                                    # Race condition likely
                                    await db.rollback()
                                    result = await db.execute(select(Tag).where(Tag.name == label))
                                    existing_tag = result.scalar_one()
                                    tag_id = existing_tag.tag_id
                            else:
                                tag_id = existing_tag.tag_id

                            # Create PhotoTag
                            # Check exists first to be safe
                            link_res = await db.execute(select(PhotoTag).where(
                                PhotoTag.photo_id == photo.photo_id,
                                PhotoTag.tag_id == tag_id
                            ))
                            if not link_res.scalar_one_or_none():
                                pt = PhotoTag(photo_id=photo.photo_id, tag_id=tag_id, confidence=score)
                                db.add(pt)

                    print(f"Classification complete.")
                    
                except ImportError:
                    print("Transformers/Torch not installed. Skipping scene detection.")
                except Exception as e:
                    print(f"Error in scene detection: {e}")

                # 4b. Filename Fallback (if no EXIF date)
                if not photo.taken_at:
                    # ... (keep existing filename logic)
                    import re
                    # ... (rest of filename logic)
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

                # Update DB
                photo.size_bytes = size_bytes
                photo.sha256 = sha256
                # Ensure phash is stored as signed 64-bit integer for Postgres BIGINT
                if phash >= 2**63:
                    phash -= 2**64
                photo.phash = phash
                
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
