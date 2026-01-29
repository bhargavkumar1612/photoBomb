
import asyncio
import os
import sys
import logging
from sqlalchemy import select

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.animal import AnimalDetection
from app.models.tag import Tag, PhotoTag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_tags():
    async with AsyncSessionLocal() as db:
        # 1. Get all animal detections
        stmt = select(AnimalDetection)
        result = await db.execute(stmt)
        detections = result.scalars().all()
        
        logger.info(f"Processing {len(detections)} animal detections for hashtags...")
        
        processed_pairs = set()
        
        for det in detections:
            tag_name = det.label.lower().replace(" ", "")
            pair = (det.photo_id, tag_name)
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)
            
            # Check/Create tag
            tag_stmt = select(Tag).where(Tag.name == tag_name)
            tag_res = await db.execute(tag_stmt)
            tag = tag_res.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=tag_name, category="animals")
                db.add(tag)
                await db.flush()
            
            # Link photo to tag
            link_stmt = select(PhotoTag).where(
                PhotoTag.photo_id == det.photo_id,
                PhotoTag.tag_id == tag.tag_id
            )
            link_res = await db.execute(link_stmt)
            if not link_res.scalar_one_or_none():
                pt = PhotoTag(photo_id=det.photo_id, tag_id=tag.tag_id, confidence=det.confidence)
                db.add(pt)
                logger.info(f"Tagged photo {det.photo_id} with #{tag_name}")
        
        await db.commit()
    logger.info("Animal tagging backfill complete.")

if __name__ == "__main__":
    asyncio.run(add_tags())
