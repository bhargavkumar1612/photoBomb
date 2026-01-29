from fastapi import APIRouter, Depends, HTTPException, Query
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

class TagResponse(BaseModel):
    tag_id: int
    name: str
    category: str
    count: int
    cover_photo_url: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[TagResponse])
async def list_tags(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List tags with photo association counts for the current user.
    Optionally filter by category (e.g., 'nature', 'places').
    """
    
    # Query: Select Tag, Count(PhotoTag) 
    # Join PhotoTag -> Photo to ensure user ownership AND non-deleted stats
    stmt = (
        select(
            Tag,
            func.count(PhotoTag.photo_id).label("photo_count")
        )
        .join(PhotoTag, PhotoTag.tag_id == Tag.tag_id)
        .join(Photo, Photo.photo_id == PhotoTag.photo_id)
        .where(
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
        .group_by(Tag.tag_id)
        .order_by(desc("photo_count"))
    )
    
    if category:
        stmt = stmt.where(Tag.category == category)
        
    result = await db.execute(stmt)
    rows = result.all()
    
    response = []
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for tag_obj, count in rows:
        # Fetch latest photo for thumbnail
        # We need a subquery or separate query
        photo_stmt = (
            select(Photo)
            .join(PhotoTag, PhotoTag.photo_id == Photo.photo_id)
            .where(
                PhotoTag.tag_id == tag_obj.tag_id,
                Photo.user_id == current_user.user_id,
                Photo.deleted_at == None
            )
            .order_by(desc(Photo.taken_at))
            .limit(1)
        )
        
        photo_res = await db.execute(photo_stmt)
        latest_photo = photo_res.scalar_one_or_none()
        
        cover_url = None
        if latest_photo:
             key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{latest_photo.photo_id}"
             cover_url = storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600)
             
        response.append(TagResponse(
            tag_id=tag_obj.tag_id,
            name=tag_obj.name,
            category=tag_obj.category,
            count=count,
            cover_photo_url=cover_url
        ))
        
    return response
