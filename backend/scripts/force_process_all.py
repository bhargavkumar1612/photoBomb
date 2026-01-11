import asyncio
import os
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.celery_app import celery_app

async def force_reprocess():
    async with AsyncSessionLocal() as db:
        # Fetch all photos to be safe
        result = await db.execute(select(Photo))
        photos = result.scalars().all()
        
        print(f"Queueing {len(photos)} photos for FULL reprocessing (metadata+thumbnails).")
        
        for photo in photos:
            # Send task
            celery_app.send_task(
                'app.workers.thumbnail_worker.process_upload', 
                args=[str(photo.photo_id), str(photo.photo_id)]
            )
            print(f"Queued: {photo.filename}")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(force_reprocess())
