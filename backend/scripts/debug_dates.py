import asyncio
import os
import sys
from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo

async def inspect_photos():
    async with AsyncSessionLocal() as db:
        # Get recent photos
        result = await db.execute(select(Photo).order_by(desc(Photo.uploaded_at)).limit(10))
        photos = result.scalars().all()
        
        print(f"{'Filename':<50} | {'Uploaded':<20} | {'Taken At':<20} | {'Processed':<20}")
        print("-" * 120)
        
        for p in photos:
            taken = str(p.taken_at) if p.taken_at else "NULL"
            uploaded = p.uploaded_at.strftime("%Y-%m-%d %H:%M")
            processed = p.processed_at.strftime("%Y-%m-%d %H:%M") if p.processed_at else "NULL"
            print(f"{p.filename[:48]:<50} | {uploaded:<20} | {taken:<20} | {processed:<20}")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(inspect_photos())
