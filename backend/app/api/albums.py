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
    thumbnail_ids: List[str] = []
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
    
    return AlbumResponse(
        album_id=str(new_album.album_id),
        name=new_album.name,
        description=new_album.description,
        cover_photo_id=str(new_album.cover_photo_id) if new_album.cover_photo_id else None,
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
    result = await db.execute(
        select(Album).where(Album.user_id == current_user.user_id)
        .order_by(Album.updated_at.desc())
    )
    albums = result.scalars().all()
    
    # Get photo counts for each album
    album_responses = []
    for album in albums:
        # Count photos in album and get recent photos for collage
        photos_result = await db.execute(
            select(album_photos.c.photo_id)
            .where(album_photos.c.album_id == album.album_id)
            .order_by(album_photos.c.added_at.desc())
        )
        all_photo_ids = photos_result.scalars().all()
        photo_count = len(all_photo_ids)
        thumbnail_ids = [str(pid) for pid in all_photo_ids[:3]] # Get first 3 photo IDs
        
        album_responses.append(AlbumResponse(
            album_id=str(album.album_id),
            name=album.name,
            description=album.description,
            cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
            thumbnail_ids=thumbnail_ids,
            photo_count=photo_count,
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
    
    photos_data = [
        {
            "photo_id": str(p.photo_id),
            "filename": p.filename,
            "mime_type": p.mime_type,
            "size_bytes": p.size_bytes,
            "uploaded_at": p.uploaded_at.isoformat(),
            "favorite": p.favorite
        }
        for p in photos
    ]
    
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
