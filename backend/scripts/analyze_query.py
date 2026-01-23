import asyncio
import sys
import os
from sqlalchemy import text

# Add backend directory to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

from app.core.database import engine

async def analyze_query():
    user_id = 'f3c3033d-68d5-4273-8f46-4b0743ff8f51' # From the curl token
    
    # Raw SQL for explain analyze since we want to see the plan for the exact query
    # The ORM generates: SELECT ... FROM photobomb.users WHERE photobomb.users.user_id = $1
    
    formatted_sql = f"EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM photobomb.users WHERE user_id = '{user_id}'"
    
    print(f"Running: {formatted_sql}")
    print("-" * 50)
    
    async with engine.connect() as conn:
        result = await conn.execute(text(formatted_sql))
        rows = result.fetchall()
        for row in rows:
            print(row[0])

if __name__ == "__main__":
    asyncio.run(analyze_query())
