"""
Test database connection performance to diagnose slow login.
"""
import time
import asyncio
from app.core.database import get_db
from app.models.user import User
from sqlalchemy import select, text

async def test_db_performance():
    print("=" * 60)
    print("Testing database connection performance")
    print("=" * 60)
    
    # Test 1: Simple ping
    print("\n1. Testing database ping:")
    async for db in get_db():
        try:
            start = time.time()
            await db.execute(text("SELECT 1"))
            ping_time = time.time() - start
            print(f"   Ping time: {ping_time:.3f}s")
        finally:
            break
    
    # Test 2: User query
    print("\n2. Testing user query:")
    async for db in get_db():
        try:
            start = time.time()
            result = await db.execute(
                select(User).where(User.email == "bhargav.tatikonda@fake.mail")
            )
            user = result.scalar_one_or_none()
            query_time = time.time() - start
            print(f"   Query time: {query_time:.3f}s")
            print(f"   User found: {user is not None}")
        finally:
            break
    
    # Test 3: Multiple sequential queries
    print("\n3. Testing 5 sequential queries:")
    start = time.time()
    for i in range(5):
        async for db in get_db():
            try:
                await db.execute(text("SELECT 1"))
            finally:
                break
    total_time = time.time() - start
    print(f"   Total time: {total_time:.3f}s")
    print(f"   Average per query: {total_time/5:.3f}s")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_db_performance())
