
import os
import sys
import asyncio
import uuid
import logging
from sqlalchemy import select, and_
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.tag import Tag, PhotoTag
from app.services.classifier import classify_image
from app.services.document_classifier import classify_document
from app.services.storage_factory import get_storage_service
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_photo_for_documents(db, photo, storage):
    try:
        # 1. Download photo to temp file
        key = f"{settings.STORAGE_PATH_PREFIX}/{photo.user_id}/{photo.photo_id}/original/{photo.filename}"
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            logger.info(f"Downloading {photo.filename}...")
            data = storage.download_file_bytes(key)
            tmp.write(data)
            tmp_path = tmp.name

        # 2. Classify (First Pass)
        logger.info(f"Classifying {photo.filename}...")
        results = classify_image(tmp_path, threshold=0.3)
        
        is_document = any(r['category'] == 'documents' for r in results)
        
        if is_document:
            logger.info(f"Document detected! Performing granular tagging...")
            doc_results = classify_document(tmp_path, threshold=0.3)
            
            for res in doc_results:
                label = res['label']
                score = res['score']
                tag_name = label.replace(" ", "")
                
                # Check/Create tag
                tag_stmt = select(Tag).where(Tag.name == tag_name)
                tag_res = await db.execute(tag_stmt)
                tag = tag_res.scalar_one_or_none()
                
                if not tag:
                    tag = Tag(name=tag_name, category="documents")
                    db.add(tag)
                    await db.flush()
                
                # Link photo to tag
                link_stmt = select(PhotoTag).where(
                    PhotoTag.photo_id == photo.photo_id,
                    PhotoTag.tag_id == tag.tag_id
                )
                link_res = await db.execute(link_stmt)
                if not link_res.scalar_one_or_none():
                    pt = PhotoTag(photo_id=photo.photo_id, tag_id=tag.tag_id, confidence=score)
                    db.add(pt)
            
            logger.info(f"Finished tagging {photo.filename}")
        else:
            logger.info(f"{photo.filename} is not a document (Scene: {results[0]['label'] if results else 'unknown'})")

        os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Error processing {photo.photo_id}: {e}")

async def main():
    async with AsyncSessionLocal() as db:
        # Get all photos (or recently uploaded ones)
        # For backfill, we process everything that isn't deleted
        stmt = select(Photo).where(Photo.deleted_at == None)
        result = await db.execute(stmt)
        photos = result.scalars().all()
        
        storage = get_storage_service(settings.STORAGE_PROVIDER)
        
        logger.info(f"Processing {len(photos)} photos for documents...")
        for photo in photos:
            await process_photo_for_documents(db, photo, storage)
            await db.commit() # Commit per photo for safety

if __name__ == "__main__":
    asyncio.run(main())
