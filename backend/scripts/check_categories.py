
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_categories():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text('SELECT DISTINCT category FROM photobomb_dev.tags'))
        categories = res.all()
        print("Existing categories:", categories)

if __name__ == "__main__":
    asyncio.run(check_categories())
