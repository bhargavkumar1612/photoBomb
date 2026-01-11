import asyncio
import os
import sys
from sqlalchemy import select, or_
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.celery_app import celery_app

async def check_and_fix_thumbnails():
    """
    Checks for photos that are missing taken_at but likely have it in filename,
    or just re-processes everything recent to be safe.
    """
    print("Checking for photos to re-process for metadata extaction...")
    
    async with AsyncSessionLocal() as db:
        # Find photos where taken_at is NULL OR just re-run all new uploads
        # Let's target all photos without taken_at or processed_at is NULL
        query = select(Photo).where(
            or_(
                Photo.processed_at == None,
                Photo.taken_at == None
            )
        )
        result = await db.execute(query)
        photos = result.scalars().all()
        
        count = len(photos)
        
        if count == 0:
            print("No photos found needing metadata update (all have taken_at or processed).")
            # Maybe force re-run for last N photos just in case the previous worker didn't extract filename date?
            # User has ~30 images. Let's force re-run them.
            print("Forcing check on *all* photos just to be sure...")
            query = select(Photo)
            result = await db.execute(query)
            photos = result.scalars().all()
            count = len(photos)

        print(f"Queueing {count} photos for re-processing.")
        print("-" * 40)
        
        for photo in photos:
            print(f"Queueing fix to: {photo.filename} ({photo.photo_id})")
            celery_app.send_task(
                'app.workers.thumbnail_worker.process_upload', 
                args=[str(photo.photo_id), str(photo.photo_id)]
            )
            
        print("-" * 40)
        print(f"Queued {count} jobs.")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    try:
        asyncio.run(check_and_fix_thumbnails())
    except KeyboardInterrupt:
        print("\nAborted.")
