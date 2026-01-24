
import asyncio
from app.services.storage_providers.b2_native_service import B2NativeService
import os

# Mock settings just in case, but code uses app.core.config which loads .env
# We assume .env is correctly loaded by app imports

def test_download():
    # User ID obtained from previous query? No, we need it.
    # We'll just construct the key manually if we know the user.
    # Wait, I don't know the USER ID for that photo!
    # Let's query it again and get user_id too.
    pass 

# Better script: query DB, get full key, try download
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.photo import Photo
from app.services.storage_providers.b2_native_service import B2NativeService

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Photo).where(Photo.storage_provider == 'b2_native').limit(1))
        photo = result.scalar_one_or_none()
        
        if not photo:
            print("No B2 photos to test.")
            return

        print(f"Testing download for Photo: {photo.filename}")
        user_id = photo.user_id
        photo_id = photo.photo_id
        
        # B2 Key Structure: uploads/{user_id}/{photo_id}/original/{filename}
        key = f"uploads/{user_id}/{photo_id}/original/{photo.filename}"
        print(f"Key: {key}")
        
        try:
            service = B2NativeService()
            print("Authorizing...")
            service.authorize()
            print("Authorized.")
            
            print("Downloading bytes...")
            data = service.download_file_bytes(key)
            print(f"Success! Downloaded {len(data)} bytes.")
            
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
