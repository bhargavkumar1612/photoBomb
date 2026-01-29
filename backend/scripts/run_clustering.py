import asyncio
import os
import sys
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.services.face_clustering import cluster_faces
from sqlalchemy import select
from app.models.user import User

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    async with AsyncSessionLocal() as db:
        # Get the first user (assuming single user for now or just pick one)
        result = await db.execute(select(User))
        user = result.scalars().first()
        
        if not user:
            logger.error("No user found in DB")
            return
            
        logger.info(f"Running clustering for user {user.email} ({user.user_id})")
        
        await cluster_faces(user.user_id)
        
    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(main())
