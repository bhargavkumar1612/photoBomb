import asyncio
import os
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from datetime import datetime

async def test_write():
    async with AsyncSessionLocal() as db:
        # Get one photo
        result = await db.execute(select(Photo).limit(1))
        photo = result.scalar_one_or_none()
        if photo:
            print(f"Updating photo {photo.photo_id}...")
            # Toggle favorite as a test
            old_fav = photo.favorite
            photo.favorite = not old_fav
            await db.commit()
            print("Write successful.")
        else:
            print("No photos.")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(test_write())
