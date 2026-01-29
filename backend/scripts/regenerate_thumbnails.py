import asyncio
import os
import sys
import tempfile
import logging
from sqlalchemy import select
from PIL import Image, ImageOps

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.core.config import settings
from app.services.storage_factory import get_storage_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_thumbnail_pil(input_path, output_path, size, format='jpeg'):
    with Image.open(input_path) as img:
        # Auto-rotate
        img = ImageOps.exif_transpose(img)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
            background.paste(img, img.split()[-1])
            img = background.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Calculate new size maintaining aspect ratio
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Save
        img.save(output_path, 'JPEG', quality=90, optimize=True)

async def process_photo_thumbnails(db, photo):
    logger.info(f"Checking thumbnails for {photo.filename} ({photo.photo_id})")
    
    storage = get_storage_service(photo.storage_provider)
    source_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
    
    tmp_path = None
    try:
        # Check if thumbnails exist? 
        # For simplicity, we just regenerate. It's safer.
        
        # Download Original
        try:
            file_bytes = storage.download_file_bytes(source_key)
        except Exception as e:
            logger.error(f"Failed to download original {source_key}: {e}")
            return

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        # Generate Thumbnails
        sizes = [256, 512, 1024]
        for size in sizes:
            thumb_key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/thumbnails/thumb_{size}.jpg"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as thumb_tmp:
                thumb_path = thumb_tmp.name
                
            try:
                generate_thumbnail_pil(tmp_path, thumb_path, size)
                
                with open(thumb_path, 'rb') as f:
                    thumb_data = f.read()
                    
                storage.upload_bytes(
                    data_bytes=thumb_data,
                    key=thumb_key,
                    content_type='image/jpeg'
                )
                logger.info(f"Uploaded {thumb_key}")
            except Exception as e:
                logger.error(f"Failed to generate/upload thumb {size}: {e}")
            finally:
                if os.path.exists(thumb_path):
                    os.unlink(thumb_path)
                    
    except Exception as e:
        logger.error(f"Error processing {photo.photo_id}: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Photo))
        photos = result.scalars().all()
        logger.info(f"Found {len(photos)} photos to process.")
        
        for photo in photos:
            await process_photo_thumbnails(db, photo)
            
    logger.info("Regeneration complete.")

if __name__ == "__main__":
    asyncio.run(main())
