import asyncio
import os
import sys
from sqlalchemy import select

# Ensure we can import app modules
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.services.b2_service import b2_service
from app.workers.thumbnail_worker import process_upload

async def rescue_thumbnails():
    print("Rescuing missing thumbnails...")
    
    async with AsyncSessionLocal() as db:
        # Get unprocessed photos
        query = select(Photo).where(Photo.processed_at == None)
        result = await db.execute(query)
        photos = result.scalars().all()
        
        print(f"Found {len(photos)} unprocessed photos.")
        
        for photo in photos:
            print(f"Checking {photo.filename} ({photo.photo_id})...")
            
            # 1. Try to find the file in B2
            # Expected pattern: uploads/{user_id}/.../original/{filename}
            prefix = f"uploads/{photo.user_id}/"
            
            # List files for user
            try:
                # We need to list enough files to find it. This might be slow if user has many files.
                # But typically listing by prefix scans recursively? Yes, recursive=True in our impl.
                files = b2_service.list_files(prefix=prefix, max_files=10000)
            except Exception as e:
                print(f"Failed to list files for user {photo.user_id}: {e}")
                continue
            
            found_file = None
            for f in files:
                # Check if it ends with /original/{filename}
                # And matches filename exactly
                if f['file_name'].endswith(f"/original/{photo.filename}"):
                    found_file = f
                    break
            
            if found_file:
                print(f"FOUND file at: {found_file['file_name']}")
                # Extract upload_id from path: uploads/{user_id}/{upload_id}/original/{filename}
                parts = found_file['file_name'].split('/')
                # parts[0]=uploads, [1]=user_id, [2]=upload_id
                if len(parts) >= 3:
                    real_upload_id = parts[2]
                    print(f"Recovered upload_id: {real_upload_id}")
                    
                    # Run process_upload synchronously
                    try:
                        print(f"Processing...")
                        # process_upload returns a Task if loop is running
                        eager_result = process_upload.apply(args=[real_upload_id, str(photo.photo_id)])
                        returned_task = eager_result.result
                        
                        if returned_task and (asyncio.iscoroutine(returned_task) or isinstance(returned_task, asyncio.Task)):
                            await returned_task
                            print("Success (Allocated Task)!")
                        else:
                            print(f"Success (Sync): {eager_result.result}")
                            
                    except Exception as e:
                        print(f"Processing failed: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("Could not parse path structure.")
            else:
                print(f"File NOT FOUND in B2 for {photo.filename}")
                
if __name__ == "__main__":
    asyncio.run(rescue_thumbnails())
