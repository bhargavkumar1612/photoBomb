
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.tag import Tag, PhotoTag
from app.models.photo import Photo
from app.api.auth import get_current_user
from app.services.storage_factory import get_storage_service
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter()

class HashtagResponse(BaseModel):
    tag_id: uuid.UUID
    name: str
    count: int
    cover_photo_url: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[HashtagResponse])
async def list_hashtags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all tags in the 'documents' category with photo counts."""
    stmt = (
        select(
            Tag,
            func.count(PhotoTag.photo_id).label("photo_count")
        )
        .join(PhotoTag, PhotoTag.tag_id == Tag.tag_id)
        .join(Photo, Photo.photo_id == PhotoTag.photo_id)
        .where(
            Tag.category.in_(["documents", "animals", "places", "place", "nature", "people"]),
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
        .group_by(Tag.tag_id)
        .order_by(desc("photo_count"))
    )
    
    result = await db.execute(stmt)
    tags_with_counts = result.all()
    
    if not tags_with_counts:
        return []

    # BATCH QUERY for cover photos to fix N+1
    tag_ids = [row[0].tag_id for row in tags_with_counts]
    cover_stmt = (
        select(PhotoTag.tag_id, Photo)
        .join(Photo, Photo.photo_id == PhotoTag.photo_id)
        .where(PhotoTag.tag_id.in_(tag_ids), Photo.deleted_at == None)
        .distinct(PhotoTag.tag_id)
    )
    cover_res = await db.execute(cover_stmt)
    cover_map = {row[0]: row[1] for row in cover_res.all()}

    response = []
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for tag, count in tags_with_counts:
        cover_photo = cover_map.get(tag.tag_id)
        
        cover_url = None
        if cover_photo:
            cover_url = storage.generate_presigned_url(
                f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{cover_photo.photo_id}/thumbnails/thumb_512.jpg",
                expires_in=3600
            )
            
        response.append(HashtagResponse(
            tag_id=tag.tag_id,
            name=tag.name,
            count=count,
            cover_photo_url=cover_url
        ))
        
    return response

@router.get("/{tag_id}/photos")
async def list_hashtag_photos(
    tag_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all photos for a specific document tag."""
    stmt = (
        select(Photo)
        .join(PhotoTag, PhotoTag.photo_id == Photo.photo_id)
        .where(
            PhotoTag.tag_id == tag_id,
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
        .order_by(desc(Photo.taken_at))
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    photos = result.scalars().all()
    
    response = []
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for photo in photos:
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        thumb_urls = {
            "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
            "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
            "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
            "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
        }
        
        response.append({
            "photo_id": str(photo.photo_id),
            "filename": photo.filename,
            "thumb_urls": thumb_urls,
            "taken_at": photo.taken_at
        })
        
    return response
