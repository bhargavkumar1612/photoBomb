"""
Photos API endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Response, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import io
import uuid
from PIL import Image, ImageOps 

from app.core.database import get_db
from app.api.auth import get_current_user, get_current_user_id
from app.models.user import User
from app.models.photo import Photo, PhotoFile
from app.services.storage_factory import get_storage_service
from app.core.config import settings

router = APIRouter()
router = APIRouter()


@router.get("/{photo_id}/download")
async def download_photo(
    photo_id: str,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Download original photo file.
    Redirects to signed URL from appropriate provider (B2 or S3).
    """
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user_id,
            Photo.deleted_at == None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    storage = get_storage_service(photo.storage_provider)
    b2_key = f"uploads/{current_user_id}/{photo.photo_id}/original/{photo.filename}"
    
    # Generate presigned download URL
    download_url = storage.generate_presigned_url(b2_key, expires_in=3600)
    
    # Redirect client
    return Response(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": download_url}
    )


@router.get("/{photo_id}/thumbnail/{size}")
async def get_thumbnail(
    photo_id: str,
    size: int,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get photo thumbnail."""
    # Validate size
    if size not in [256, 512, 1024]:
        size = 512
        
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user_id,
            Photo.deleted_at == None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    storage = get_storage_service(photo.storage_provider)
    thumb_key = f"uploads/{current_user_id}/{photo_id}/thumbnails/thumb_{size}.jpg"
    
    # Generate presigned URL
    thumb_url = storage.generate_presigned_url(thumb_key, expires_in=3600)
    
    # Redirect client
    return Response(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": thumb_url}
    )


# Pydantic schemas
class PhotoResponse(BaseModel):
    photo_id: str
    filename: str
    mime_type: str
    size_bytes: int
    taken_at: Optional[datetime]
    uploaded_at: datetime
    caption: Optional[str]
    favorite: bool
    archived: bool
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    location_name: Optional[str] = None
    thumb_urls: dict
    
    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    photos: List[PhotoResponse]
    next_cursor: Optional[str]
    has_more: bool


class UpdatePhotoRequest(BaseModel):
    caption: Optional[str] = None
    favorite: Optional[bool] = None
    archived: Optional[bool] = None


@router.get("", response_model=PhotoListResponse)
async def list_photos(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=200),
    sort: str = Query("taken_desc", regex="^(created_desc|created_asc|taken_desc|taken_asc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's photos in timeline view.
    
    Supports pagination with cursor and sorting options.
    """
    # Build query
    query = select(Photo).where(
        Photo.user_id == current_user.user_id,
        Photo.deleted_at == None,
        Photo.storage_provider == settings.STORAGE_PROVIDER
    )
    
    # Apply sorting
    if sort == "taken_desc":
        query = query.order_by(desc(Photo.taken_at))
    elif sort == "taken_asc":
        query = query.order_by(Photo.taken_at)
    elif sort == "created_desc":
        query = query.order_by(desc(Photo.uploaded_at))
    else:  # created_asc
        query = query.order_by(Photo.uploaded_at)
    
    # Limit results
    query = query.limit(limit + 1)  # Fetch one extra to check has_more
    
    result = await db.execute(query)
    photos = result.scalars().all()
    
    has_more = len(photos) > limit
    if has_more:
        photos = photos[:limit]
    
    # Generate presigned/authorized URL for download
    
    # Build response
    photo_responses = []
    
    # Strict mode: We only show photos for the current provider, so we use that provider's service.
    storage = get_storage_service(settings.STORAGE_PROVIDER)
    
    for photo in photos:
        # storage = get_storage_service(photo.storage_provider) # Removed per strict isolation request
        
        # Construct full keys
        key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
        
        # Generate generic thumbnail URLs (signed)
        thumb_urls = {
            "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
            "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
            "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
            # Also provide the original download URL here for convenience
             "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
        }
        
        # We can add a "download_url" field to PhotoResponse if we want, 
        # or just rely on the frontend knowing to use "original" or constructing it?
        # The prompt asked to put it in headers or frontend, but here we are providing FULL URLs.
        # Frontend logic expects `thumb_urls` dict.
        
        p_resp = PhotoResponse(
            photo_id=str(photo.photo_id),
            filename=photo.filename,
            mime_type=photo.mime_type,
            size_bytes=photo.size_bytes,
            taken_at=photo.taken_at,
            uploaded_at=photo.uploaded_at,
            caption=photo.caption,
            favorite=photo.favorite,
            archived=photo.archived,
            gps_lat=float(photo.gps_lat) if photo.gps_lat else None,
            gps_lng=float(photo.gps_lng) if photo.gps_lng else None,
            location_name=photo.location_name,
            thumb_urls=thumb_urls
        )
        # Dynamically attach download_url to the response object if schema supports it? 
        # Schema doesn't have it. `thumb_urls` is a dict, so I effectively added "original" key to it.
        # Let's verify schema.
        
        photo_responses.append(p_resp)
    
    return PhotoListResponse(
        photos=photo_responses,
        next_cursor=None,  # TODO: Generate cursor from last photo
        has_more=has_more
    )


@router.get("/map", response_model=List[PhotoResponse])
async def get_map_photos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all photos that have GPS coordinates.
    Optimized for map view (lighter payload if needed, but reusing PhotoResponse for now).
    """
    result = await db.execute(
        select(Photo).where(
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None,
            Photo.gps_lat != None,
            Photo.gps_lng != None,
            Photo.storage_provider == settings.STORAGE_PROVIDER
        )
    )
    photos = result.scalars().all()
    
    storage = get_storage_service(settings.STORAGE_PROVIDER)
    photo_responses = []
    
    for photo in photos:
        key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
        
        # We only need small thumbnail for map markers
        thumb_urls = {
            "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
        }
        
        photo_responses.append(PhotoResponse(
            photo_id=str(photo.photo_id),
            filename=photo.filename,
            mime_type=photo.mime_type,
            size_bytes=photo.size_bytes,
            taken_at=photo.taken_at,
            uploaded_at=photo.uploaded_at,
            caption=photo.caption,
            favorite=photo.favorite,
            archived=photo.archived,
            gps_lat=float(photo.gps_lat) if photo.gps_lat else None,
            gps_lng=float(photo.gps_lng) if photo.gps_lng else None,
            location_name=photo.location_name,
            thumb_urls=thumb_urls
        ))
        
    return photo_responses


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get photo metadata by ID."""
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Strict isolation
    storage = get_storage_service(settings.STORAGE_PROVIDER)
    
    # Generate thumbnail URLs
    key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
    thumb_urls = {
        "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
        "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
        "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
        "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
    }
    
    return PhotoResponse(
        photo_id=str(photo.photo_id),
        filename=photo.filename,
        mime_type=photo.mime_type,
        size_bytes=photo.size_bytes,
        taken_at=photo.taken_at,
        uploaded_at=photo.uploaded_at,
        caption=photo.caption,
        favorite=photo.favorite,
        archived=photo.archived,
        thumb_urls=thumb_urls
    )


@router.patch("/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: str,
    request: UpdatePhotoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update photo metadata (caption, favorite, archived)."""
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Update fields
    if request.caption is not None:
        photo.caption = request.caption
    if request.favorite is not None:
        photo.favorite = request.favorite
    if request.archived is not None:
        photo.archived = request.archived
    
    photo.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(photo)
    
    thumb_urls = {
        "thumb_256": f"/api/v1/photos/{photo.photo_id}/thumbnail/256",
        "thumb_512": f"/api/v1/photos/{photo.photo_id}/thumbnail/512",
        "thumb_1024": f"/api/v1/photos/{photo.photo_id}/thumbnail/1024",
    }
    
    return PhotoResponse(
        photo_id=str(photo.photo_id),
        filename=photo.filename,
        mime_type=photo.mime_type,
        size_bytes=photo.size_bytes,
        taken_at=photo.taken_at,
        uploaded_at=photo.uploaded_at,
        caption=photo.caption,
        favorite=photo.favorite,
        archived=photo.archived,
        thumb_urls=thumb_urls
    )




@router.patch("/{photo_id}/favorite", status_code=status.HTTP_200_OK)
async def toggle_favorite(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle favorite status of a photo."""
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Toggle favorite
    photo.favorite = not photo.favorite
    await db.commit()
    
    return {"favorite": photo.favorite}


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete a photo (moves to trash). Does NOT delete from B2 storage."""
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Soft delete in database only
    photo.deleted_at = datetime.utcnow()
    
    # Note: We do NOT reduce storage quota here because the file still exists in B2
    # Quota is reduced only on permanent delete
    
    await db.commit()
    
    return None


@router.get("/trash/list", response_model=PhotoListResponse)
async def get_trash(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List photos in trash (deleted_at is not null)."""
    # Build query for deleted photos
    query = select(Photo).where(
        Photo.user_id == current_user.user_id,
        Photo.deleted_at != None
    ).order_by(desc(Photo.deleted_at))
    
    # Limit results
    query = query.limit(limit + 1)
    
    result = await db.execute(query)
    photos = result.scalars().all()
    
    has_more = len(photos) > limit
    if has_more:
        photos = photos[:limit]
    
    storage = get_storage_service()

    # Build response
    photo_responses = []
    for photo in photos:
        key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
        
        thumb_urls = {
            "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
            "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
            "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
            "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
        }
        
        photo_responses.append(PhotoResponse(
            photo_id=str(photo.photo_id),
            filename=photo.filename,
            mime_type=photo.mime_type,
            size_bytes=photo.size_bytes,
            taken_at=photo.taken_at,
            uploaded_at=photo.uploaded_at,
            caption=photo.caption,
            favorite=photo.favorite,
            archived=photo.archived,
            thumb_urls=thumb_urls
        ))
    
    return PhotoListResponse(
        photos=photo_responses,
        next_cursor=None, # TODO: Implement cursor if needed
        has_more=has_more
    )


@router.post("/{photo_id}/restore", status_code=status.HTTP_200_OK)
async def restore_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore a photo from trash."""
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id,
            Photo.deleted_at != None
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found in trash"
        )
    
    # Restore
    photo.deleted_at = None
    await db.commit()
    
    return {"status": "restored"}


@router.delete("/{photo_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanently_delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete a photo from B2 and database."""
    # Find photo (checked deleted and non-deleted to allow deleting directly if needed, 
    # but usually from trash so we check for user ownership)
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id == photo_id,
            Photo.user_id == current_user.user_id
        )
    )
    photo = result.scalar_one_or_none()
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Delete from Storage
    storage = get_storage_service(photo.storage_provider)
    try:
        # List and delete all files (original + thumbnails)
        prefix = f"uploads/{current_user.user_id}/{photo.photo_id}"
        files = storage.list_files(prefix=prefix)
        for f in files:
            # delete_file expects 'key' (file_name)
            storage.delete_file(f['file_name'])
            
    except Exception as e:
        print(f"Warning: Failed to delete file from Storage: {str(e)}")
        # Proceed to DB delete anyway to free up quota in our system
    
    # Hard delete from database
    await db.delete(photo)
    
    # Update user storage quota
    current_user.storage_used_bytes -= photo.size_bytes
    if current_user.storage_used_bytes < 0:
        current_user.storage_used_bytes = 0
        
    await db.commit()
    
    return None


