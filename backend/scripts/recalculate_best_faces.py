import asyncio
import os
import sys
import logging
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.person import Face, Person
from app.core.config import settings
from app.services.storage_factory import get_storage_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def find_best_face(db, person):
    """
    Find the best face for a person based on resolution (width * height).
    """
    # Fetch all faces for this person
    result = await db.execute(
        select(Face)
        .where(Face.person_id == person.person_id)
    )
    faces = result.scalars().all()
    
    if not faces:
        return None

    best_face = None
    max_area = 0
    
    for face in faces:
        width = face.location_right - face.location_left
        height = face.location_bottom - face.location_top
        area = width * height
        
        if area > max_area:
            max_area = area
            best_face = face
            
    return best_face

async def main():
    async with AsyncSessionLocal() as db:
        # Get all people
        result = await db.execute(select(Person))
        people = result.scalars().all()
        logger.info(f"Found {len(people)} people to check.")
        
        updated_count = 0
        
        for person in people:
            best_face = await find_best_face(db, person)
            
            if best_face and best_face.face_id != person.cover_face_id:
                logger.info(f"Updating cover for {person.name} ({person.person_id}) to face {best_face.face_id} (Area: {(best_face.location_right - best_face.location_left) * (best_face.location_bottom - best_face.location_top)})")
                person.cover_face_id = best_face.face_id
                updated_count += 1
        
        if updated_count > 0:
            await db.commit()
            logger.info(f"Updated {updated_count} people with better cover photos.")
        else:
            logger.info("No updates needed.")

if __name__ == "__main__":
    asyncio.run(main())
