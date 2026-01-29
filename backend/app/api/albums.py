"""
Albums API endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.album import Album, album_photos, album_contributors
from app.models.photo import Photo
from app.services.storage_factory import get_storage_service
from app.core.config import settings
from sqlalchemy.orm import selectinload

router = APIRouter()

# Pydantic schemas
class ContributorRequest(BaseModel):
    email: str

class ContributorResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    
    class Config:
        from_attributes = True

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
    contributors: List[ContributorResponse] = []

    class Config:
        from_attributes = True


class AlbumDetailResponse(AlbumResponse):
    photos: List[dict]
    is_owner: bool = True # Helper for frontend to know if they can manage contributors


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
        storage = get_storage_service()
        key = f"uploads/{current_user.user_id}/{new_album.cover_photo_id}/thumbnails/thumb_512.jpg"
        cover_url = storage.generate_presigned_url(key)

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
    """Get all albums for current user (owned + shared)."""
    from sqlalchemy import func, and_
    
    # 1. Fetch albums (Owned + Shared)
    result = await db.execute(
        select(Album)
        .outerjoin(album_contributors, Album.album_id == album_contributors.c.album_id)
        .options(
            selectinload(Album.contributors),
            selectinload(Album.cover_photo)
        )
        .where(
            or_(
                Album.user_id == current_user.user_id,
                album_contributors.c.user_id == current_user.user_id
            )
        )
        .order_by(Album.updated_at.desc())
        .distinct()
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
    
    # Generate Signed URLs
    storage = get_storage_service()
    
    # Need to know uploader for each photo to sign url? 
    # Current limitation: thumbnails are stored as uploads/{owner_id}/{photo_id}.
    # The Album List query for thumbnails gives us Photo IDs.
    # WE DO NOT KNOW the user_id of the photo from the bulk query above!
    # The current `sign_thumb` function uses `current_user.user_id`.
    # THIS IS A BUG for shared albums! If I see a shared album, the cover photo might not be mine.
    # The thumbnails might not be mine.
    
    # Fix: We need to fetch the user_id (owner) for the thumbnails.
    # I should change the thumb_stmt to join with photos table and fetch user_id.
    
    # Redoing step 3 to include photo owner.
    
    subq_owner = (
        select(
            album_photos.c.album_id, 
            album_photos.c.photo_id,
            Photo.user_id.label("photo_owner_id"),
            func.row_number().over(
                partition_by=album_photos.c.album_id,
                order_by=album_photos.c.added_at.desc()
            ).label("rn")
        )
        .join(Photo, Photo.photo_id == album_photos.c.photo_id)
        .where(album_photos.c.album_id.in_(album_ids))
        .subquery()
    )
    
    thumb_stmt_owner = (
         select(subq_owner.c.album_id, subq_owner.c.photo_id, subq_owner.c.photo_owner_id)
         .where(subq_owner.c.rn <= 3)
    )
    
    thumb_result_owner = await db.execute(thumb_stmt_owner)
    
    thumbs_info_map = {aid: [] for aid in album_ids}
    for row in thumb_result_owner.all():
        # row: album_id, photo_id, photo_owner_id
        thumbs_info_map[row[0]].append({
            "id": str(row[1]),
            "owner_id": str(row[2])
        })


    def sign_thumb_with_owner(photo_id, owner_id, size=512):
         key = f"uploads/{owner_id}/{photo_id}/thumbnails/thumb_{size}.jpg"
         return storage.generate_presigned_url(key, expires_in=86400)

    # 4. Assemble response
    album_responses = []
    
    # Also need to handle Album Cover Photo Owner!
    # The album object has cover_photo_id. We lazy loaded it? No.
    # We should eager load cover_photo.
    # To fix cover photo URL, we need to fetch cover photo details or Preload it.
    
    # Let's optimize step 1 to preload cover_photo
    # I'll rely on a separate specific fix or efficient query if possible.
    # For now, let's assume cover photo is likely one of the thumbnails or we need to fetch it.
    # The simplest way to avoid N+1 is `selectinload(Album.cover_photo)`.
    
    # I will modify Step 1 in a separate small edit if needed, or assume I can't change it here easily without re-writing the whole block.
    # Wait, I AM rewriting the whole block. I should add `selectinload(Album.cover_photo)`.
    
    for album in albums:
        # Cover photo
        cover_url = None
        if album.cover_photo:
             # If we preloaded it
             cover_url = sign_thumb_with_owner(album.cover_photo_id, album.cover_photo.user_id, 512)
        elif album.cover_photo_id:
             # Fallback if not loaded (though we should load it)
             # Try to find owner in thumbs if it happens to be there?
             # Or assume current user (risky). 
             # Let's rely on preloading `cover_photo` in the query.
             pass
            
        # Thumbnails list
        t_infos = thumbs_info_map.get(album.album_id, [])
        t_ids = [t['id'] for t in t_infos]
        t_urls = [sign_thumb_with_owner(t['id'], t['owner_id'], 512) for t in t_infos]
        
        # Contributors mapping
        contrib_list = [
            ContributorResponse(
                user_id=str(c.user_id),
                full_name=c.full_name,
                email=c.email
            ) for c in album.contributors
        ]
        
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
            updated_at=album.updated_at,
            contributors=contrib_list
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
    # Check access: Owner OR Contributor
    result = await db.execute(
        select(Album)
        .outerjoin(album_contributors, Album.album_id == album_contributors.c.album_id)
        .options(selectinload(Album.contributors))
        .where(
            Album.album_id == album_id,
            or_(
                Album.user_id == current_user.user_id,
                album_contributors.c.user_id == current_user.user_id
            )
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    is_owner = (album.user_id == current_user.user_id)

    # Get photos in album
    # Need to join with Photo.user to get photo owner name
    photos_result = await db.execute(
        select(Photo)
        .join(album_photos, Photo.photo_id == album_photos.c.photo_id)
        .options(selectinload(Photo.user))
        .where(album_photos.c.album_id == album.album_id)
        .order_by(album_photos.c.added_at.desc())
    )
    photos = photos_result.scalars().all()
    
    # Generate Signed URLs
    storage = get_storage_service()
    
    def sign_b2_url(key: str) -> str:
        return storage.generate_presigned_url(key, expires_in=86400)

    photos_data = []
    for p in photos:
        # Photo owner
        p_owner_id = p.user_id
        p_owner_name = p.user.full_name if p.user else "Unknown"
        
        key_base = f"uploads/{p_owner_id}/{p.photo_id}"
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
            "caption": p.caption, 
            "taken_at": p.taken_at,
            "owner": {
                "user_id": str(p_owner_id),
                "name": p_owner_name
            }
        })
    
    contrib_list = [
        ContributorResponse(
            user_id=str(c.user_id),
            full_name=c.full_name,
            email=c.email
        ) for c in album.contributors
    ]

    return AlbumDetailResponse(
        album_id=str(album.album_id),
        name=album.name,
        description=album.description,
        cover_photo_id=str(album.cover_photo_id) if album.cover_photo_id else None,
        photo_count=len(photos_data),
        created_at=album.created_at,
        updated_at=album.updated_at,
        photos=photos_data,
        contributors=contrib_list,
        is_owner=is_owner
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


@router.post("/{album_id}/contributors", response_model=List[ContributorResponse])
async def add_contributor(
    album_id: str,
    contributor: ContributorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a contributor to an album by email."""
    # 1. Verify album ownership (only owner can add contributors)
    result = await db.execute(
        select(Album)
        .options(selectinload(Album.contributors))
        .where(Album.album_id == album_id, Album.user_id == current_user.user_id)
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found or you are not the owner"
        )
    
    # 2. Find user by email
    user_result = await db.execute(select(User).where(User.email == contributor.email))
    user_to_add = user_result.scalar_one_or_none()
    
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User with this email not found")
        
    if user_to_add.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You are the owner")

    # 3. Check if already contributor
    if user_to_add in album.contributors:
        raise HTTPException(status_code=400, detail="User is already a contributor")
        
    # 4. Add contributor
    # Insert directly into association table or append to relationship
    # Since we loaded contributors, appending might work but inserting to table is safer/explicit
    # import uuid if needed, or use values
    # album.contributors.append(user_to_add) # This should work with async session if properly managed, but explicit INSERT preferred for massive concurency or clarity
    
    # Using append with selectinload works fine in SQLAlchemy 2.0+ async usually, but let's be explicit
    stmt = album_contributors.insert().values(
        album_id=album.album_id,
        user_id=user_to_add.user_id
    )
    await db.execute(stmt)
    await db.commit()
    
    # Reload contributors for response
    await db.refresh(album, attribute_names=["contributors"])
    
    return [
        ContributorResponse(
            user_id=str(c.user_id),
            full_name=c.full_name,
            email=c.email
        ) for c in album.contributors
    ]


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
    # Verify album exists and user is owner OR contributor
    result = await db.execute(
        select(Album)
        .outerjoin(album_contributors, Album.album_id == album_contributors.c.album_id)
        .where(
            Album.album_id == album_id,
            or_(
                Album.user_id == current_user.user_id,
                album_contributors.c.user_id == current_user.user_id
            )
        )
    )
    album = result.scalar_one_or_none()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found or permission denied"
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
    # Verify album exists and user is owner OR contributor
    album_result = await db.execute(
        select(Album)
        .outerjoin(album_contributors, Album.album_id == album_contributors.c.album_id)
        .where(
            Album.album_id == album_id,
            or_(
                Album.user_id == current_user.user_id,
                album_contributors.c.user_id == current_user.user_id
            )
        )
    )
    if not album_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found or permission denied"
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
