import asyncio
import os
import sys
import tempfile
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from PIL import Image

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.person import Face, Person
from app.models.photo import Photo
from app.core.config import settings
from app.services.storage_factory import get_storage_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_face_crop(db, face):
    logger.info(f"Processing face {face.face_id} from photo {face.photo_id}")
    
    if not face.photo:
        logger.warning("Face has no associated photo loaded.")
        return

    storage = get_storage_service(face.photo.storage_provider)
    source_key = f"{settings.STORAGE_PATH_PREFIX}/{face.photo.user_id}/{face.photo.photo_id}/original/{face.photo.filename}"
    crop_key = f"{settings.STORAGE_PATH_PREFIX}/{face.photo.user_id}/faces/{face.face_id}.jpg"
    
    tmp_path = None
    try:
        # Download Original
        try:
            file_bytes = storage.download_file_bytes(source_key)
        except Exception as e:
            logger.error(f"Failed to download original {source_key}: {e}")
            return

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        # Crop Face
        with Image.open(tmp_path) as img:
            # Face location: top, right, bottom, left
            # Ensure coordinates are within bounds
            width, height = img.size
            top = max(0, face.location_top)
            right = min(width, face.location_right)
            bottom = min(height, face.location_bottom)
            left = max(0, face.location_left)
            
            # Add some padding (margin)
            margin = 0.4 # 40% margin
            face_width = right - left
            face_height = bottom - top
            
            top = max(0, int(top - face_height * margin))
            bottom = min(height, int(bottom + face_height * margin))
            left = max(0, int(left - face_width * margin))
            right = min(width, int(right + face_width * margin))
            
            face_img = img.crop((left, top, right, bottom))
            
            # Resize for consistency (e.g., 256x256 max)
            face_img.thumbnail((256, 256))
            
            # Save to buffer
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as crop_tmp:
                crop_path = crop_tmp.name
                
            face_img.save(crop_path, "JPEG", quality=90)
            
            with open(crop_path, 'rb') as f:
                crop_data = f.read()
                
            storage.upload_bytes(
                data_bytes=crop_data,
                key=crop_key,
                content_type='image/jpeg'
            )
            logger.info(f"Uploaded face crop {crop_key}")
            
            if os.path.exists(crop_path):
                os.unlink(crop_path)
                    
    except Exception as e:
        logger.error(f"Error processing face {face.face_id}: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

async def main():
    async with AsyncSessionLocal() as db:
        # Fetch all faces with photos
        result = await db.execute(
            select(Face).options(selectinload(Face.photo))
        )
        faces = result.scalars().all()
        logger.info(f"Found {len(faces)} faces to process.")
        
        for face in faces:
            await process_face_crop(db, face)
            
    logger.info("Face crop generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
