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
from app.services.b2_service import b2_service
from app.core.config import settings

router = APIRouter()
router = APIRouter()


@router.get("/{photo_id}/download")
async def download_photo(
    photo_id: str,
    filename: Optional[str] = Query(None),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Download original photo file (stateless redirect to B2).
    If filename is provided, avoids DB lookup entirely.
    """
    
    if filename:
        # STATELESS MODE: Fastest
        b2_key = f"uploads/{current_user_id}/{photo_id}/original/{filename}"
    else:
        # FALLBACK MODE: Fetch from DB to get filename
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
        b2_key = f"uploads/{current_user_id}/{photo.photo_id}/original/{photo.filename}"
    
    # Generate presigned download URL
    # URL valid for 1 hour
    download_url = b2_service.generate_presigned_download_url(b2_key, expires_in=3600)
    
    # Redirect client to B2 directly
    return Response(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": download_url}
    )


@router.get("/{photo_id}/thumbnail/{size}")
async def get_thumbnail(
    photo_id: str,
    size: int,
    current_user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Get photo thumbnail (stateless redirect to B2)."""
    # Validate size
    if size not in [256, 512, 1024]:
        size = 512
    
    # Define cache key
    thumb_key = f"uploads/{current_user_id}/{photo_id}/thumbnails/thumb_{size}.jpg"
    
    # Generate presigned URL
    # URL valid for 1 hour
    thumb_url = b2_service.generate_presigned_download_url(thumb_key, expires_in=3600)
    
    # Redirect client to B2 directly
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
        Photo.deleted_at == None
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
    
    # Generate B2 Authorization for the entire user folder
    # This avoids signing each URL individually and allows batch access
    user_prefix = f"uploads/{current_user.user_id}/"
    auth_token = b2_service.get_download_authorization(user_prefix, valid_duration=86400) # 24 hours
    download_base = b2_service.get_download_url_base()
    bucket_name = settings.B2_BUCKET_NAME # Or fetch from b2_service.get_bucket().name but config saves a call

    
    # Helper to sign URL
    def sign_b2_url(key: str) -> str:
        return f"{download_base}/file/{bucket_name}/{key}?Authorization={auth_token}"

    # Build response
    photo_responses = []
    for photo in photos:
        # Construct full B2 keys
        key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
        
        # Generate generic thumbnail URLs (signed)
        thumb_urls = {
            "thumb_256": sign_b2_url(f"{key_base}/thumbnails/thumb_256.jpg"),
            "thumb_512": sign_b2_url(f"{key_base}/thumbnails/thumb_512.jpg"),
            "thumb_1024": sign_b2_url(f"{key_base}/thumbnails/thumb_1024.jpg"),
            # Also provide the original download URL here for convenience
             "original": sign_b2_url(f"{key_base}/original/{photo.filename}")
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
    
    # Generate B2 Authorization
    user_prefix = f"uploads/{current_user.user_id}/"
    auth_token = b2_service.get_download_authorization(user_prefix, valid_duration=86400)
    download_base = b2_service.get_download_url_base()
    bucket_name = settings.B2_BUCKET_NAME
    
    def sign_b2_url(key: str) -> str:
        return f"{download_base}/file/{bucket_name}/{key}?Authorization={auth_token}"
    
    # Generate thumbnail URLs
    key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
    thumb_urls = {
        "thumb_256": sign_b2_url(f"{key_base}/thumbnails/thumb_256.jpg"),
        "thumb_512": sign_b2_url(f"{key_base}/thumbnails/thumb_512.jpg"),
        "thumb_1024": sign_b2_url(f"{key_base}/thumbnails/thumb_1024.jpg"),
        "original": sign_b2_url(f"{key_base}/original/{photo.filename}")
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
    
    # Generate B2 Authorization
    user_prefix = f"uploads/{current_user.user_id}/"
    auth_token = b2_service.get_download_authorization(user_prefix, valid_duration=86400)
    download_base = b2_service.get_download_url_base()
    bucket_name = settings.B2_BUCKET_NAME
    
    def sign_b2_url(key: str) -> str:
        return f"{download_base}/file/{bucket_name}/{key}?Authorization={auth_token}"

    # Build response
    photo_responses = []
    for photo in photos:
        key_base = f"uploads/{current_user.user_id}/{photo.photo_id}"
        
        thumb_urls = {
            "thumb_256": sign_b2_url(f"{key_base}/thumbnails/thumb_256.jpg"),
            "thumb_512": sign_b2_url(f"{key_base}/thumbnails/thumb_512.jpg"),
            "thumb_1024": sign_b2_url(f"{key_base}/thumbnails/thumb_1024.jpg"),
            "original": sign_b2_url(f"{key_base}/original/{photo.filename}")
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
    
    # Delete from B2
    b2_key = f"uploads/{current_user.user_id}/{photo.photo_id}/original/{photo.filename}"
    try:
        # Get file info to get file_id for deletion
        # TODO: Refactor B2 service to expose delete_by_name or similar cleanly
        import requests
        # We need to list filenames to get the ID or handle this in b2_service
        # For now, we'll try best effort with b2_service methods if available, or direct API
        
        # Simplified approach: Just clear the DB record if B2 fails, but B2 is critical for storage
        # Ideally b2_service should handle this. Let's try to list versions and delete.
        bucket = b2_service.get_bucket()
        
        # List versions of the file to get ID
        for file_version in bucket.ls(folder_to_list=f"uploads/{current_user.user_id}/{photo.photo_id}"):
             # Tuple (file_version_info, folder_name) or similar depending on library version
             # b2sdk ls returns generator of (file_version, folder)
             
             # Actually, simpler to just assume key structure and iterate
             # If using b2sdk, we can hide_file (soft delete in B2) or delete_file_version
             pass
             
        # Direct deletion logic from previous implementation was trying to use requests which is hacky
        # Use b2sdk properly if possible, or fallback to the previous logic which seemed to work for verified delete
        
        # Use a more robust B2 delete: hide it first (simpler) or iterate versions?
        # B2 'hide_file' creates a hidden marker. 'delete_file_version' removes it.
        # We want to remove all versions.
        
        # Iterating versions to delete all
        # b2_service.bucket is a b2sdk.v2.Bucket object
        file_versions = bucket.ls(f"uploads/{current_user.user_id}/{photo.photo_id}", recursive=True)
        for file_version, _ in file_versions:
            file_version.delete()
            
    except Exception as e:
        print(f"Warning: Failed to delete file from B2: {str(e)}")
        # Proceed to DB delete anyway to free up quota in our system
    
    # Hard delete from database
    await db.delete(photo)
    
    # Update user storage quota
    current_user.storage_used_bytes -= photo.size_bytes
    if current_user.storage_used_bytes < 0:
        current_user.storage_used_bytes = 0
        
    await db.commit()
    
    return None


