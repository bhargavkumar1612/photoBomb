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

from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print(f"\\n{'='*50}")
print(f"CONFIGURATION CHECK:")
print(f"DB_SCHEMA:        {settings.DB_SCHEMA}")
print(f"{'='*50}\\n")

async def main():
    async with AsyncSessionLocal() as db:
        # Run for ALL users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users to cluster faces for.")

        for user in users:
            logger.info(f"--------------------------------------------------")
            logger.info(f"Running clustering for user {user.email} ({user.user_id})")
            await cluster_faces(user.user_id)
        
    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(main())
