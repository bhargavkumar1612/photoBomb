"""
Albums API endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.album import Album, album_photos
from app.models.photo import Photo
from app.services.b2_service import b2_service
from app.core.config import settings

router = APIRouter()


# Pydantic schemas
class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None
    cover_photo_id: Optional[str] = None


class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cover_photo_id: Optional[str] = None


class AlbumResponse(BaseModel):
    album_id: str
    name: str
    description: Optional[str]
    cover_photo_id: Optional[str]
    cover_photo_url: Optional[str] = None
    thumbnail_ids: List[str] = [] # Deprecated but kept for compatibility if needed
    thumbnail_urls: List[str] = []
    photo_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlbumDetailResponse(AlbumResponse):
    photos: List[dict]


# Create album
@router.post("", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    album_data: AlbumCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new album."""
    # Validate cover photo belongs to user if provided
    if album_data.cover_photo_id:
        result = await db.execute(
            select(Photo).where(
                Photo.photo_id == album_data.cover_photo_id,
                Photo.user_id == current_user.user_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover photo not found"
            )
    
    new_album = Album(
        user_id=current_user.user_id,
        name=album_data.name,
        description=album_data.description,
        cover_photo_id=album_data.cover_photo_id
    )
    
    db.add(new_album)
    await db.commit()
    await db.refresh(new_album)
    
    # Generate URL if cover photo exists
    cover_url = None
    if new_album.cover_photo_id:
        user_prefix = f"uploads/{current_user.user_id}/"
        auth_token = b2_service.get_download_authorization(user_prefix)
        download_base = b2_service.get_download_url_base()
        bucket_name = settings.B2_BUCKET_NAME
        key = f"{user_prefix}{new_album.cover_photo_id}/thumbnails/thumb_512.jpg"
        cover_url = f"{download_base}/file/{bucket_name}/{key}?Authorization={auth_token}"

    return AlbumResponse(
        album_id=str(new_album.album_id),
        name=new_album.name,
        description=new_album.description,
        cover_photo_id=str(new_album.cover_photo_id) if new_album.cover_photo_id else None,
        cover_photo_url=cover_url,
        photo_count=0,
        created_at=new_album.created_at,
        updated_at=new_album.updated_at
    )


# List albums
@router.get("", response_model=List[AlbumResponse])
async def list_albums(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all albums for current user."""
    from sqlalchemy import func, and_
    
    # 1. Fetch albums
    result = await db.execute(
        select(Album).where(Album.user_id == current_user.user_id)
        .order_by(Album.updated_at.desc())
    )
    albums = result.scalars().all()
    
    if not albums:
        return []
        
    album_ids = [a.album_id for a in albums]
    
    # 2. Bulk fetch photo counts
    count_stmt = (
        select(album_photos.c.album_id, func.count(album_photos.c.photo_id))
        .where(album_photos.c.album_id.in_(album_ids))
        .group_by(album_photos.c.album_id)
    )
    count_result = await db.execute(count_stmt)
    counts_map = {row[0]: row[1] for row in count_result.all()}
    
    # 3. Bulk fetch thumbnails using window function (Top 3 per album)
    # Subquery to assign row numbers partition by album
    subq = (
        select(
            album_photos.c.album_id, 
            album_photos.c.photo_id,
            func.row_number().over(
                partition_by=album_photos.c.album_id,
                order_by=album_photos.c.added_at.desc()
            ).label("rn")
        )
        .where(album_photos.c.album_id.in_(album_ids))
        .subquery()
    )
    
    # Filter where row number <= 3
    thumb_stmt = (
        select(subq.c.album_id, subq.c.photo_id)
        .where(subq.c.rn <= 3)
    )
    thumb_result = await db.execute(thumb_stmt)
    
    # Group thumbnails by album
    thumbs_map = {aid: [] for aid in album_ids}
    for row in thumb_result.all():
        thumbs_map[row[0]].append(str(row[1]))
    
    # Generate B2 Token for Signing
    user_prefix = f"uploads/{current_user.user_id}/"
    auth_token = b2_service.get_download_authorization(user_prefix, valid_duration=86400)
    download_base = b2_service.get_download_url_base()
    bucket_name = settings.B2_BUCKET_NAME
    
    def sign_thumb(photo_id, size=512):
         key = f"{user_prefix}{photo_id}/thumbnails/thumb_{size}.jpg"
         return f"{download_base}/file/{bucket_name}/{key}?Authorization={auth_token}"

    # 4. Assemble response
    album_responses = []
    for album in albums:
        # Cover photo
        cover_url = None
        if album.cover_photo_id:
            cover_url = sign_thumb(album.cover_photo_id, 512)
            
        # Thumbnails list
        # Map IDs to signed URLs. Use 256 for list thumbnails? 
        # Existing Frontend used 512 then 200, 200.
        # B2 supports 256. 
        # Let's use 256 for the list to save bandwidth, or 512 if quality needed.
        # Given the grid, 256 should be fine. But let's stick to 512 for now to match 'cover' quality or mix.
        # Actually frontend `Albums.jsx` specifically requests `thumbnail/512` for [0] and `thumbnail/200` for [1],[2].
        # I'll enable 512 for all in this list for simplicity.
        
        t_ids = thumbs_map.get(album.album_id, [])
        t_urls = [sign_thumb(pid, 512) for pid in t_ids]
        
        album_responses.append(AlbumResponse(
            album_id=str(album.album_id),
            name=album.name,
            description=album.description,
            cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
            cover_photo_url=cover_url,
            thumbnail_ids=t_ids,
            thumbnail_urls=t_urls,
            photo_count=counts_map.get(album.album_id, 0),
            created_at=album.created_at,
            updated_at=album.updated_at
        ))
    
    return album_responses


# Get album details
@router.get("/{album_id}", response_model=AlbumDetailResponse)
async def get_album(
    album_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get album details with photos."""
    result = await db.execute(
        select(Album).where(
            Album.album_id == album_id,
            Album.user_id == current_user.user_id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Get photos in album
    photos_result = await db.execute(
        select(Photo)
        .join(album_photos, Photo.photo_id == album_photos.c.photo_id)
        .where(album_photos.c.album_id == album.album_id)
        .order_by(album_photos.c.added_at.desc())
    )
    photos = photos_result.scalars().all()
    
    # Generate B2 Token
    user_prefix = f"uploads/{current_user.user_id}/"
    auth_token = b2_service.get_download_authorization(user_prefix, valid_duration=86400)
    download_base = b2_service.get_download_url_base()
    bucket_name = settings.B2_BUCKET_NAME
    
    def sign_b2_url(key: str) -> str:
        return f"{download_base}/file/{bucket_name}/{key}?Authorization={auth_token}"

    photos_data = []
    for p in photos:
        key_base = f"uploads/{current_user.user_id}/{p.photo_id}"
        thumb_urls = {
            "thumb_256": sign_b2_url(f"{key_base}/thumbnails/thumb_256.jpg"),
            "thumb_512": sign_b2_url(f"{key_base}/thumbnails/thumb_512.jpg"),
            "thumb_1024": sign_b2_url(f"{key_base}/thumbnails/thumb_1024.jpg"),
            "original": sign_b2_url(f"{key_base}/original/{p.filename}")
        }
        
        photos_data.append({
            "photo_id": str(p.photo_id),
            "filename": p.filename,
            "mime_type": p.mime_type,
            "size_bytes": p.size_bytes,
            "uploaded_at": p.uploaded_at.isoformat(),
            "favorite": p.favorite,
            "thumb_urls": thumb_urls,
            "caption": p.caption, # Added caption just in case
            "taken_at": p.taken_at # Added taken_at if needed
        })
    
    return AlbumDetailResponse(
        album_id=str(album.album_id),
        name=album.name,
        description=album.description,
        cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
        photo_count=len(photos_data),
        created_at=album.created_at,
        updated_at=album.updated_at,
        photos=photos_data
    )


# Update album
@router.patch("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: str,
    album_data: AlbumUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update album metadata."""
    result = await db.execute(
        select(Album).where(
            Album.album_id == album_id,
            Album.user_id == current_user.user_id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Update fields if provided
    if album_data.name is not None:
        album.name = album_data.name
    if album_data.description is not None:
        album.description = album_data.description
    if album_data.cover_photo_id is not None:
        album.cover_photo_id = album_data.cover_photo_id
    
    album.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(album)
    
    # Get photo count
    count_result = await db.execute(
        select(album_photos).where(album_photos.c.album_id == album.album_id)
    )
    photo_count = len(count_result.all())
    
    return AlbumResponse(
        album_id=str(album.album_id),
        name=album.name,
        description=album.description,
        cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
        photo_count=photo_count,
        created_at=album.created_at,
        updated_at=album.updated_at
    )


# Delete album
@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an album (photos are not deleted, only removed from album)."""
    result = await db.execute(
        select(Album).where(
            Album.album_id == album_id,
            Album.user_id == current_user.user_id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    await db.delete(album)
    await db.commit()


@router.post("/{album_id}/photos", status_code=status.HTTP_201_CREATED)
async def add_photos_to_album(
    album_id: str,
    photo_ids: List[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add multiple photos to an album."""
    # Verify album exists and belongs to user
    result = await db.execute(
        select(Album).where(
            Album.album_id == album_id,
            Album.user_id == current_user.user_id
        )
    )
    album = result.scalar_one_or_none()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )

    # Verify photos exist and belong to user
    # Simplified check: just fetch them
    photos_result = await db.execute(
        select(Photo.photo_id).where(
            Photo.photo_id.in_(photo_ids),
            Photo.user_id == current_user.user_id
        )
    )
    valid_photo_ids = photos_result.scalars().all()
    
    if not valid_photo_ids:
        raise HTTPException(status_code=400, detail="No valid photos found")

    # Insert into junction table
    # We should use ON CONFLICT DO NOTHING or checks to avoid duplicates
    # For simplicity, we check existence first or catch integrity errors?
    # Better: explicit check.
    
    # Get existing associations
    existing_result = await db.execute(
        select(album_photos.c.photo_id).where(
            album_photos.c.album_id == album_id,
            album_photos.c.photo_id.in_(valid_photo_ids)
        )
    )
    existing_ids = set(str(pid) for pid in existing_result.scalars().all())
    
    # Filter out already added
    new_ids = [pid for pid in valid_photo_ids if str(pid) not in existing_ids]
    
    if new_ids:
        values = [{"album_id": album_id, "photo_id": pid, "added_at": datetime.utcnow()} for pid in new_ids]
        await db.execute(album_photos.insert(), values)
        
        # Update album updated_at
        album.updated_at = datetime.utcnow()
        await db.commit()
        
    return {"added_count": len(new_ids), "existing_count": len(existing_ids)}


@router.delete("/{album_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_photo_from_album(
    album_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a photo from an album."""
    # Verify album ownership
    result = await db.execute(
        select(Album).where(Album.album_id == album_id, Album.user_id == current_user.user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Album not found")
        
    # Delete from junction table
    await db.execute(
        delete(album_photos).where(
            album_photos.c.album_id == album_id,
            album_photos.c.photo_id == photo_id
        )
    )
    await db.commit()



# Add photo to album
@router.post("/{album_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_photo_to_album(
    album_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a photo to an album."""
    # Verify album belongs to user
    album_result = await db.execute(
        select(Album).where(
            Album.album_id == album_id,
            Album.user_id == current_user.user_id
        )
    )
    if not album_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Verify photo belongs to user
    photo_result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id
        )
    )
    if not photo_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Check if already in album
    existing = await db.execute(
        select(album_photos).where(
            album_photos.c.album_id == album_id,
            album_photos.c.photo_id == photo_id
        )
    )
    if existing.scalar_one_or_none():
        return  # Already in album, just return success
    
    # Add to album
    import uuid
    await db.execute(
        album_photos.insert().values(
            album_id=uuid.UUID(album_id),
            photo_id=uuid.UUID(photo_id),
            added_at=datetime.utcnow()
        )
    )
    await db.commit()


# Remove photo from album
@router.delete("/{album_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_photo_from_album(
    album_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a photo from an album."""
    # Verify album belongs to user
    album_result = await db.execute(
        select(Album).where(
            Album.album_id == album_id,
            Album.user_id == current_user.user_id
        )
    )
    if not album_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Remove from album
    import uuid
    await db.execute(
        delete(album_photos).where(
            album_photos.c.album_id == uuid.UUID(album_id),
            album_photos.c.photo_id == uuid.UUID(photo_id)
        )
    )
    await db.commit()
