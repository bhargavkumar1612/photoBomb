
import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text
from uuid import UUID

# Load env
backend_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', '.env')
load_dotenv(backend_env)
# Script is in root photoBomb/debug_hashtags.py
# Backend is in photoBomb/backend
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app.core.database import AsyncSessionLocal

TARGET_TAG_UUID = "b2e08b46-0821-436b-8c1b-16dc269e09f1"

async def analyze_hashtags():
    async with AsyncSessionLocal() as db:
        print(f"\n{'='*50}")
        print(f"RCA: Hashtag Analysis")
        print(f"{'='*50}\n")
        
        # 1. Inspect the specific troublesome tag
        print(f"1. Inspecting Tag UUID: {TARGET_TAG_UUID}")
        try:
            res = await db.execute(text("SELECT tag_id, name, category, created_at FROM photobomb.tags WHERE tag_id = :tag_id"), {"tag_id": TARGET_TAG_UUID})
            tag = res.fetchone()
            if tag:
                print(f"   FAST CHECK: Found in `tags` table.")
                print(f"   - Name: {tag.name}")
                print(f"   - Category: {tag.category}")
            else:
                print(f"   FAST CHECK: NOT FOUND in `tags` table.")
        except Exception as e:
            print(f"   Error querying tag: {e}")

        # 2. Check Photo Links for this tag
        print(f"\n2. Checking associated photos in `photo_tags`")
        try:
            res = await db.execute(text("""
                SELECT count(*) 
                FROM photobomb.photo_tags pt 
                JOIN photobomb.photos p ON pt.photo_id = p.photo_id
                WHERE pt.tag_id = :tag_id
            """), {"tag_id": TARGET_TAG_UUID})
            count = res.scalar()
            print(f"   - Total Linked Photos (via photo_tags): {count}")
            
            if count > 0:
                # Check how many are valid (not deleted, matching user?)
                res = await db.execute(text("""
                    SELECT p.photo_id, p.filename, p.deleted_at, p.user_id 
                    FROM photobomb.photo_tags pt 
                    JOIN photobomb.photos p ON pt.photo_id = p.photo_id
                    WHERE pt.tag_id = :tag_id
                    LIMIT 5
                """), {"tag_id": TARGET_TAG_UUID})
                print(f"   - Sample Photos:")
                for row in res:
                    print(f"     * {row.filename} (Deleted: {row.deleted_at}) [User: {row.user_id}]")
            else:
                print(f"   - No photos linked. This explains '0 Photos'.")

        except Exception as e:
            print(f"   Error checking photo links: {e}")

        # 3. Check for UUID-named tags (Data Pollution)
        print(f"\n3. Checking for UUID-like tag names (Potential Bugs)")
        res = await db.execute(text("SELECT tag_id, name FROM photobomb.tags WHERE name ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'"))
        uuid_tags = res.all()
        if uuid_tags:
            print(f"   - Found {len(uuid_tags)} tags that look like UUIDs:")
            for t in uuid_tags[:5]:
                print(f"     * {t.name} (ID: {t.tag_id})")
        else:
            print(f"   - No UUID-named tags found.")
            
        # 4. Check Top Tags by Count
        print(f"\n4. Top 5 Tags by Photo Count")
        res = await db.execute(text("""
            SELECT t.name, t.category, count(pt.photo_id) as cnt
            FROM photobomb.tags t
            JOIN photobomb.photo_tags pt ON t.tag_id = pt.tag_id
            GROUP BY t.tag_id, t.name, t.category
            ORDER BY cnt DESC
            LIMIT 5
        """))
        for row in res:
            print(f"   - {row.name} ({row.category}): {row.cnt}")
            
if __name__ == "__main__":
    asyncio.run(analyze_hashtags())
