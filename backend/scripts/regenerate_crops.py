import asyncio
import os
import sys
import tempfile
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env explicitly
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print(f"Warning: .env not found at {env_path}")

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.person import Face
from app.models.animal import AnimalDetection
from app.core.config import settings
from app.services.storage_factory import get_storage_service
from app.workers.thumbnail_worker import save_crop

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_photo_crops(db, photo, faces, animals, storage):
    if not faces and not animals:
        return

    logger.info(f"Checking crops for Photo {photo.photo_id} ({len(faces)} faces, {len(animals)} animals)")
    
    missing_faces = []
    missing_animals = []
    
    # Check Faces
    for face in faces:
        key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/faces/{face.face_id}.jpg"
        if not storage.file_exists(key):
            missing_faces.append(face)
            
    # Check Animals
    for animal in animals:
        key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/animals/crops/{animal.detection_id}.jpg"
        if not storage.file_exists(key):
            missing_animals.append(animal)
            
    if not missing_faces and not missing_animals:
        logger.info("All crops exist.")
        return

    logger.info(f"Regenerating {len(missing_faces)} faces and {len(missing_animals)} animals...")
    
    try:
        # Download Original
        source_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
        file_bytes = storage.download_file_bytes(source_key)
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        # Regenerate Faces
        for face in missing_faces:
            box = (face.location_top, face.location_right, face.location_bottom, face.location_left)
            key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/faces/{face.face_id}.jpg"
            if save_crop(storage, tmp_path, box, key, padding=0.4):
                logger.info(f"Restored Face {face.face_id}")
            else:
                logger.error(f"Failed to restore Face {face.face_id}")

        # Regenerate Animals
        for animal in missing_animals:
            box = (animal.location_top, animal.location_right, animal.location_bottom, animal.location_left)
            key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/animals/crops/{animal.detection_id}.jpg"
            if save_crop(storage, tmp_path, box, key, padding=0.1):
                logger.info(f"Restored Animal {animal.detection_id}")
            else:
                logger.error(f"Failed to restore Animal {animal.detection_id}")
                
    except Exception as e:
        logger.error(f"Error processing photo {photo.photo_id}: {e}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)

async def main():
    logger.info("Starting Crop Regeneration Script...")
    
    async with AsyncSessionLocal() as db:
        storage = get_storage_service(settings.STORAGE_PROVIDER)
        logger.info(f"Using Storage Provider: {settings.STORAGE_PROVIDER}")
        
        # Fetch all photos that have faces or animals
        # This might be heavy, so we can verify integrity photo by photo
        
        result = await db.execute(
            select(Photo)
            .options(selectinload(Photo.faces), selectinload(Photo.animal_detections))
            .where(Photo.deleted_at == None)
        )
        photos = result.scalars().all()
        
        logger.info(f"Scanning {len(photos)} photos...")
        for photo in photos:
            await process_photo_crops(db, photo, photo.faces, photo.animal_detections, storage)
            
    logger.info("Regeneration Complete.")

if __name__ == "__main__":
    asyncio.run(main())
