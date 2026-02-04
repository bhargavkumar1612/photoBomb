import asyncio
import sys
import os
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def make_admin(email: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User {email} not found!")
            return

        user.is_admin = True
        await db.commit()
        print(f"✅ User {email} is now an ADMIN.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/set_admin.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    asyncio.run(make_admin(email))
