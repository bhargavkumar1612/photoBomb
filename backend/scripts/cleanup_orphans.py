import asyncio
import os
import sys
import logging
import argparse
from sqlalchemy import select

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.person import Face
from app.core.config import settings
from app.services.storage_factory import get_storage_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main(dry_run=True):
    mode = "DRY RUN" if dry_run else "LIVE DELETE"
    logger.info(f"Starting cleanup in {mode} mode.")

    async with AsyncSessionLocal() as db:
        # 1. Fetch all valid IDs from database
        logger.info("Fetching valid photo and face IDs from database...")
        photo_res = await db.execute(select(Photo.photo_id))
        valid_photo_ids = {str(pid) for pid in photo_res.scalars().all()}
        
        face_res = await db.execute(select(Face.face_id))
        valid_face_ids = {str(fid) for fid in face_res.scalars().all()}
        
        logger.info(f"Found {len(valid_photo_ids)} valid photos and {len(valid_face_ids)} valid faces.")

        # 2. Get storage service
        # Using S3/R2 usually but factory handles it
        storage = get_storage_service(settings.STORAGE_PROVIDER)
        
        # 3. Scan storage for orphans
        # Pattern 1: uploads/{user_id}/{photo_id}/thumbnails/...
        # Pattern 2: uploads/{user_id}/faces/{face_id}.jpg
        
        prefix = settings.STORAGE_PATH_PREFIX
        logger.info(f"Scanning storage with prefix: {prefix}")
        
        all_files = storage.list_files(prefix, max_files=10000)
        logger.info(f"Found {len(all_files)} files in storage under prefix '{prefix}'")

        orphans = []
        
        for file_info in all_files:
            key = file_info['file_id']
            parts = key.split('/')
            
            # Check if it matches face pattern: {prefix}/{user_id}/faces/{face_id}.jpg
            if len(parts) >= 4 and parts[-2] == "faces":
                face_filename = parts[-1]
                face_id = face_filename.split('.')[0]
                if face_id not in valid_face_ids:
                    logger.warning(f"Orphaned Face found: {key}")
                    orphans.append(key)
                continue

            # Check if it matches thumbnail pattern: {prefix}/{user_id}/{photo_id}/thumbnails/...
            if len(parts) >= 5 and parts[-2] == "thumbnails":
                photo_id = parts[-3]
                if photo_id not in valid_photo_ids:
                    logger.warning(f"Orphaned Thumbnail found: {key}")
                    orphans.append(key)
                continue
                
            # Note: We don't delete 'original' folders here as they are more critical.
            # Only cleaning up generated artifacts (thumbnails, faces).

        if not orphans:
            logger.info("No orphans found. Everything is clean!")
            return

        logger.info(f"Summary: Found {len(orphans)} orphaned files.")
        
        if dry_run:
            logger.info("Dry run complete. No files were deleted.")
        else:
            logger.info(f"Deleting {len(orphans)} orphaned files...")
            for key in orphans:
                try:
                    storage.delete_file(key)
                    logger.info(f"Deleted: {key}")
                except Exception as e:
                    logger.error(f"Failed to delete {key}: {e}")
            logger.info("Cleanup complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup orphaned storage files.")
    parser.add_argument("--confirm", action="store_true", help="Perform actual deletion (default is dry run).")
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=not args.confirm))
