
import asyncio
import os
import sys
import tempfile
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.animal import Animal, AnimalDetection
from app.core.config import settings
from app.services.storage_factory import get_storage_service
from app.services.animal_detector import detect_animals, get_animal_embedding
from app.services.animal_clustering import cluster_animals
from app.workers.thumbnail_worker import save_crop

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_photo_for_animals(db, photo, storage):
    logger.info(f"Processing photo {photo.photo_id} ({photo.filename}) for animals")
    
    source_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
    
    tmp_path = None
    try:
        # Download Original
        file_bytes = storage.download_file_bytes(source_key)
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        # 1. Detect Animals
        detections = detect_animals(tmp_path, threshold=0.7)
        logger.info(f"Found {len(detections)} animals in {photo.filename}")
        
        for det in detections:
            # Check if detection already exists to avoid duplicates if run multiple times
            # Simplified: just delete existing detections for this photo first?
            # Or just check label + box...
            
            # DETR box: [xmin, ymin, xmax, ymax]
            # Convert to (top, right, bottom, left) for save_crop
            xmin, ymin, xmax, ymax = det['box']
            box = (int(ymin), int(xmax), int(ymax), int(xmin))
            
            embedding = get_animal_embedding(tmp_path, det['box'])
            
            new_det = AnimalDetection(
                photo_id=photo.photo_id,
                label=det['label'],
                confidence=det['confidence'],
                embedding=embedding,
                location_top=box[0],
                location_right=box[1],
                location_bottom=box[2],
                location_left=box[3]
            )
            db.add(new_det)
            await db.flush()
            
            # Save animal crop
            animal_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/animals/crops/{new_det.detection_id}.jpg"
            save_crop(storage, tmp_path, box, animal_key, padding=0.1)
            
    except Exception as e:
        logger.error(f"Error processing photo {photo.photo_id}: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

async def main():
    async with AsyncSessionLocal() as db:
        # 0. Optional: Clear existing detections if you want a clean start
        # await db.execute(text("DELETE FROM animal_detections"))
        # await db.execute(text("DELETE FROM animals"))
        
        # 1. Fetch all photos
        result = await db.execute(select(Photo).where(Photo.deleted_at == None))
        photos = result.scalars().all()
        logger.info(f"Found {len(photos)} photos to process for animals.")
        
        storage = get_storage_service(settings.STORAGE_PROVIDER)
        
        for photo in photos:
            # Check if already processed (has detections)?
            det_check = await db.execute(select(AnimalDetection).where(AnimalDetection.photo_id == photo.photo_id))
            if det_check.scalar_one_or_none():
                logger.info(f"Photo {photo.photo_id} already has animal detections. Skipping.")
                continue
                
            await process_photo_for_animals(db, photo, storage)
            await db.commit() # Commit per photo for progress
            
        # 2. Run clustering for all users who had photos processed
        user_ids = list(set([p.user_id for p in photos]))
        for user_id in user_ids:
            logger.info(f"Running animal clustering for user {user_id}...")
            await cluster_animals(user_id)
            
    logger.info("Animal processing backfill complete.")

if __name__ == "__main__":
    asyncio.run(main())
