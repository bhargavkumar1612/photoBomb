"""
Photos API endpoints for CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Response, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, delete
import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict
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
    b2_key = f"{settings.STORAGE_PATH_PREFIX}/{current_user_id}/{photo.photo_id}/original/{photo.filename}"
    
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
    thumb_key = f"{settings.STORAGE_PATH_PREFIX}/{current_user_id}/{photo_id}/thumbnails/thumb_{size}.jpg"
    
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
    tags: List[str] = []
    
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
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's photos in timeline view.
    
    Supports pagination with cursor and sorting options.
    """
    # Build query
    query = select(Photo).options(selectinload(Photo.visual_tags)).where(
        Photo.user_id == current_user.user_id,
        Photo.deleted_at == None,
        Photo.storage_provider == settings.STORAGE_PROVIDER
    )
    
    # Filter by tag if provided
    if tag:
        # Join with PhotoTag and Tag
        from app.models.tag import Tag, PhotoTag
        query = query.join(PhotoTag, PhotoTag.photo_id == Photo.photo_id)\
                     .join(Tag, Tag.tag_id == PhotoTag.tag_id)\
                     .where(Tag.name == tag)
    
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
    
    # Helper for safe float conversion
    import math
    def safe_float(val):
        if val is None:
            return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except (ValueError, TypeError):
            return None

    for photo in photos:
        # storage = get_storage_service(photo.storage_provider) # Removed per strict isolation request
        
        # Construct full keys
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        
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
            gps_lat=safe_float(photo.gps_lat),
            gps_lng=safe_float(photo.gps_lng),
            location_name=photo.location_name,
            thumb_urls=thumb_urls,
            tags=[t.name for t in photo.visual_tags] if hasattr(photo, 'visual_tags') else []
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

    # Local helper for map too (or move to util if used more widely)
    import math
    def safe_float(val):
        if val is None: return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f): return None
            return f
        except: return None
    
    for photo in photos:
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        
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
            gps_lat=safe_float(photo.gps_lat),
            gps_lng=safe_float(photo.gps_lng),
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
    key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
    thumb_urls = {
        "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
        "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
        "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
        "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
    }
    
    # Safe float helper
    import math
    def safe_float(val):
        if val is None: return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f): return None
            return f
        except: return None

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
        gps_lat=safe_float(photo.gps_lat),
        gps_lng=safe_float(photo.gps_lng),
        location_name=photo.location_name,
        thumb_urls=thumb_urls,
        tags=[t.name for t in photo.visual_tags] if hasattr(photo, 'visual_tags') else []
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
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        
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
        prefix = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        files = storage.list_files(prefix=prefix)
        for f in files:
            # delete_file expects 'key' (file_name)
            storage.delete_file(f['file_id'])
            
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



class BatchPhotoRequest(BaseModel):
    photo_ids: List[str]


@router.post("/batch/delete", status_code=status.HTTP_204_NO_CONTENT)
async def batch_soft_delete(
    request: BatchPhotoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch soft-delete photos."""
    if not request.photo_ids:
        return None

    # Update deleted_at for all owned photos in the list
    await db.execute(
        sa.update(Photo)
        .where(
            Photo.photo_id.in_(request.photo_ids),
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
        .values(deleted_at=datetime.utcnow())
    )
    
    await db.commit()
    return None


@router.post("/batch/restore", status_code=status.HTTP_200_OK)
async def batch_restore(
    request: BatchPhotoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch restore photos from trash."""
    if not request.photo_ids:
        return {"status": "success", "count": 0}

    result = await db.execute(
        sa.update(Photo)
        .where(
            Photo.photo_id.in_(request.photo_ids),
            Photo.user_id == current_user.user_id,
            Photo.deleted_at != None
        )
        .values(deleted_at=None)
    )
    
    await db.commit()
    # rowcount for update in asyncpg: result.rowcount
    return {"status": "restored", "count": result.rowcount}


@router.post("/batch/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def batch_permanent_delete(
    request: BatchPhotoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch permanently delete photos from B2 and database."""
    if not request.photo_ids:
        return None

    # Fetch photos first to get storage info
    result = await db.execute(
        select(Photo).where(
            Photo.photo_id.in_(request.photo_ids),
            Photo.user_id == current_user.user_id
        )
    )
    photos = result.scalars().all()
    
    if not photos:
        return None
        
    for photo in photos:
        # Delete from Storage
        storage = get_storage_service(photo.storage_provider)
        try:
            prefix = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
            files = storage.list_files(prefix=prefix)
            for f in files:
                storage.delete_file(f['file_id'])
        except Exception as e:
            print(f"Warning: Failed to delete file for photo {photo.photo_id}: {str(e)}")
        
        # Update user quota
        current_user.storage_used_bytes -= photo.size_bytes
        if current_user.storage_used_bytes < 0:
            current_user.storage_used_bytes = 0
            
    # Delete from DB
    await db.execute(
        sa.delete(Photo).where(
            Photo.photo_id.in_([p.photo_id for p in photos])
        )
    )
    
    await db.commit()
    await db.commit()
    return None


@router.post("/rescan", status_code=status.HTTP_202_ACCEPTED)
async def rescan_photos(
    process_all: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger background processing (Rescan) for photos.
    If process_all is True, rescans ALL photos.
    If False, rescans photos that might be missing metadata (processed_at is None).
    """
    from app.celery_app import celery_app
    
    query = select(Photo).where(
        Photo.user_id == current_user.user_id,
        Photo.deleted_at == None
    )
    
    if not process_all:
        # Only unprocessed
        query = query.where(Photo.processed_at == None)
        
    result = await db.execute(query)
    photos = result.scalars().all()
    
    count = 0
    for photo in photos:
        # We pass upload_id=photo_id to indicate the file is already in its final location
        celery_app.send_task(
            'app.workers.thumbnail_worker.process_photo_initial',
            args=[str(photo.photo_id), str(photo.photo_id)]
        )
        count += 1
        
    return {
        "message": f"Triggered rescan for {count} photos.",
        "count": count
    }
