
import asyncio
from sqlalchemy import text
from app.celery_app import celery_app
from app.core.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.db_keepalive_worker.keep_db_alive")
def keep_db_alive():
    """
    Periodic task to keep the Supabase database alive by performing a simple read query.
    """
    async def _process():
        async with AsyncSessionLocal() as db:
            try:
                # Perform a simple read query
                await db.execute(text("SELECT 1"))
                logger.info("Database keep-alive query successful.")
                return True
            except Exception as e:
                logger.error(f"Database keep-alive query failed: {e}")
                return False

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(_process())
