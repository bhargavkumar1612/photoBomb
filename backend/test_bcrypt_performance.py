"""
Test bcrypt performance to diagnose slow login issue.
"""
import time
import asyncio
from app.core.security import verify_password, get_password_hash
from app.core.database import get_db
from app.models.user import User
from sqlalchemy import select

async def test_bcrypt():
    print("=" * 60)
    print("Testing bcrypt performance")
    print("=" * 60)
    
    # Test 1: Hash and verify with current settings
    print("\n1. Testing hash and verify with current settings:")
    start = time.time()
    test_hash = get_password_hash("FakePassword@1")
    hash_time = time.time() - start
    print(f"   Hash time: {hash_time:.3f}s")
    print(f"   Hash: {test_hash[:60]}...")
    
    start = time.time()
    result = verify_password("FakePassword@1", test_hash)
    verify_time = time.time() - start
    print(f"   Verify time: {verify_time:.3f}s")
    print(f"   Result: {result}")
    
    # Test 2: Check actual user password hash from database
    print("\n2. Checking actual user password hash from database:")
    async for db in get_db():
        try:
            result = await db.execute(
                select(User).where(User.email == "bhargav.tatikonda@fake.mail")
            )
            user = result.scalar_one_or_none()
            
            if user and user.password_hash:
                print(f"   User found: {user.email}")
                print(f"   Hash prefix: {user.password_hash[:60]}...")
                
                # Extract bcrypt rounds from hash
                # Format: $2b$<rounds>$<salt><hash>
                if user.password_hash.startswith("$2b$"):
                    rounds = user.password_hash.split("$")[2]
                    print(f"   Bcrypt rounds in hash: {rounds}")
                
                start = time.time()
                result = verify_password("FakePassword@1", user.password_hash)
                verify_time = time.time() - start
                print(f"   Verify time: {verify_time:.3f}s")
                print(f"   Result: {result}")
            else:
                print("   User not found or no password hash")
        finally:
            break
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_bcrypt())
