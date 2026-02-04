import asyncio
import os
import sys

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete, text
from app.core.database import AsyncSessionLocal
from app.models.tag import Tag, PhotoTag
from app.models.photo import Photo

async def cleanup():
    print("🧹 Starting Hashtag Cleanup...")
    async with AsyncSessionLocal() as db:
        
        # 1. Clean PhotoTags for photos that are soft-deleted or fully deleted
        print("1. Checking for PhotoTags linking to deleted photos...")
        
        # NOTE: PhotoTag has ondelete="CASCADE" for hard deletes, 
        # but for soft deletes (deleted_at IS NOT NULL), we might want to keep them 
        # OR remove them depending on business logic. 
        # If we remove them, we can't restore the tags if we restore the photo.
        # However, sticking to the user request: "not deleted or deprecated".
        # Usually, if a photo is in trash, its tags shouldn't count towards the global tag list.
        # But if we delete the PhotoTag link, restoring the photo won't restore tags.
        # A safer approach for "cleanup" of *orphaned* tags is to just check active photos.
        # But if we want to remove the tag itself from the global list if it's ONLY used by deleted photos,
        # we need to be careful.
        
        # Strategy:
        # We will Delete Tags where NO ACTIVE (non-deleted) photo uses it.
        # We will NOT delete PhotoTags for soft-deleted photos strictly, to allow Restore.
        # Wait, if we delete the Tag, the foreign key in PhotoTag (if it exists) might block it or cascade.
        # PhotoTag -> Tag is CASCADE. So if we delete Tag, it deletes the link.
        # So if we delete a Tag because it's only on deleted photos, we break the restore capability for those photos' tags.
        
        # Revised Strategy based on "orphaned":
        # Delete Tags that have NO PhotoTags at all.
        # AND (Optionally) Delete Tags that ONLY link to deleted photos?
        # Let's stick to true orphans (0 PhotoTags) first.
        
        # Step A: Delete Orphaned Tags (No links at all)
        print("   - Identifying fully orphaned tags (0 links)...")
        # Subquery: select tag_ids that exist in photo_tags
        alive_tags_stmt = select(PhotoTag.tag_id).distinct()
        
        # Delete Tags NOT IN alive_tags
        delete_stmt = delete(Tag).where(Tag.tag_id.not_in(alive_tags_stmt))
        
        result = await db.execute(delete_stmt)
        print(f"   - Removed {result.rowcount} fully orphaned tags (no links).")
        
        # Step B: Remove Tag links for HARD deleted photos (if cascades failed) implies orphaned photo_tags
        # But FK ondelete=CASCADE should handle hard deletes.
        
        await db.commit()
        print("✅ Cleanup Complete!")

if __name__ == "__main__":
    asyncio.run(cleanup())
