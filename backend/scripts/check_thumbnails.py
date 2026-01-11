import asyncio
import os
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.celery_app import celery_app

async def check_and_fix_thumbnails():
    """
    Checks for photos that haven't been processed (missing thumbnails/metadata)
    and queues them for processing.
    """
    print("Checking for photos with missing thumbnails (processed_at is NULL)...")
    
    async with AsyncSessionLocal() as db:
        # Find photos where processed_at is NULL
        # This indicates the worker job either didn't run or failed
        query = select(Photo).where(Photo.processed_at == None)
        result = await db.execute(query)
        photos = result.scalars().all()
        
        count = len(photos)
        
        if count == 0:
            print("All photos appear to be processed! (No records with processed_at=NULL)")
            return

        print(f"Found {count} unprocessed photos.")
        print("-" * 40)
        
        for photo in photos:
            print(f"Queueing fix to: {photo.filename} ({photo.photo_id})")
            
            # We pass photo_id as upload_id assuming the file is at the correct path 
            # (which is true for direct uploads, and we have no way to recover lost upload_ids for presigned ones anyway)
            celery_app.send_task(
                'app.workers.thumbnail_worker.process_upload', 
                args=[str(photo.photo_id), str(photo.photo_id)]
            )
            
        print("-" * 40)
        print(f"Queued {count} jobs. Check Celery worker logs for progress.")

if __name__ == "__main__":
    # Ensure we can import app modules
    sys.path.append(os.getcwd())
    
    try:
        asyncio.run(check_and_fix_thumbnails())
    except KeyboardInterrupt:
        print("\nAborted.")
