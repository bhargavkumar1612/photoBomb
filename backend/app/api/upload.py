"""
Upload API endpoints for presigned URL generation and upload confirmation.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.photo import Photo
from app.services.b2_service import b2_service
from app.celery_app import celery_app

router = APIRouter()


# Pydantic schemas
class PresignRequest(BaseModel):
    filename: str
    size_bytes: int
    mime_type: str
    sha256: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "IMG_1234.jpg",
                "size_bytes": 5242880,
                "mime_type": "image/jpeg",
                "sha256": "a3c8f9e7b2d4e1a6b5c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"
            }
        }


class PresignResponse(BaseModel):
    upload_id: str
    presigned_url: str
    authorization_token: str
    b2_key: str
    expires_at: str
    multipart_chunk_size: int = 5242880  # 5MB


class ConfirmRequest(BaseModel):
    upload_id: str
    etags: Optional[list] = None


class ConfirmResponse(BaseModel):
    photo_id: str
    status: str
    estimated_completion: int = 30  # seconds


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(
    request: PresignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate presigned URL for direct browser-to-B2 upload.
    
    Checks for duplicate photos based on SHA256 hash.
    Returns 409 if duplicate found.
    """
    # Check file size against quota
    if request.size_bytes > current_user.storage_quota_bytes - current_user.storage_used_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Storage quota exceeded. Available: {(current_user.storage_quota_bytes - current_user.storage_used_bytes) / 1024 / 1024:.2f} MB"
        )
    
    # Check for duplicate based on SHA256
    result = await db.execute(
        select(Photo).where(
            Photo.user_id == current_user.user_id,
            Photo.sha256 == request.sha256,
            Photo.deleted_at == None
        )
    )
    existing_photo = result.scalar_one_or_none()
    
    if existing_photo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate",
                "photo_id": str(existing_photo.photo_id),
                "message": f"This photo was already uploaded on {existing_photo.uploaded_at.strftime('%Y-%m-%d')}"
            }
        )
    
    # Generate upload_id
    upload_id = str(uuid.uuid4())
    
    # Get presigned URL from B2
    try:
        presign_data = b2_service.generate_presigned_upload_url(
            filename=request.filename,
            user_id=str(current_user.user_id),
            upload_id=upload_id
        )
    except Exception as e:
        import traceback
        print(f"B2 Error: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )
    
    #  Store upload session in database (for tracking)
    # TODO: Create UploadSession model and store here
    
    return PresignResponse(
        upload_id=upload_id,
        presigned_url=presign_data["upload_url"],
        authorization_token=presign_data["authorization_token"],
        b2_key=presign_data["b2_key"],
        expires_at=presign_data["expires_at"]
    )


@router.post("/confirm", response_model=ConfirmResponse, status_code=status.HTTP_202_ACCEPTED)
async def confirm_upload(
    request: ConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm upload completion and trigger async processing.
    
    Creates a placeholder photo record and enqueues processing job.
    """
    # TODO: Verify upload_id exists in upload_sessions table
    
    # Create placeholder photo record
    photo = Photo(
        user_id=current_user.user_id,
        filename="placeholder.jpg",  # Will be updated by worker
        mime_type="image/jpeg",
        size_bytes=0,  # Will be updated
        sha256="",  # Will be updated
        uploaded_at=datetime.utcnow()
    )
    
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    
    # Enqueue Celery job for processing
    celery_app.send_task('app.workers.thumbnail_worker.process_upload', args=[request.upload_id, str(photo.photo_id)])
    
    return ConfirmResponse(
        photo_id=str(photo.photo_id),
        status="processing"
    )
"""
Direct upload endpoint - bypasses CORS by uploading through backend
"""
from fastapi import UploadFile

@router.post("/direct", response_model=ConfirmResponse, status_code=status.HTTP_202_ACCEPTED)
async def direct_upload(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
   Direct upload through backend (bypasses CORS).
    Backend receives file and uploads to B2.
    """
    import hashlib
    import tempfile
    import os
    from datetime import datetime
    
    # Read file content
    file_content = await file.read()
    
    # Compute SHA256
    sha256_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check for duplicates
    result = await db.execute(
        select(Photo).where(
            Photo.user_id == current_user.user_id,
            Photo.sha256 == sha256_hash,
            Photo.deleted_at == None
        )
    )
    existing_photo = result.scalar_one_or_none()
    
    if existing_photo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This photo was already uploaded on {existing_photo.uploaded_at.strftime('%Y-%m-%d')}"
        )
    
    # Check quota
    if len(file_content) > current_user.storage_quota_bytes - current_user.storage_used_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Storage quota exceeded"
        )
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file_content)
        temp_path = temp_file.name
    
    # Detect MIME type from filename if content_type is unreliable
    import mimetypes
    detected_mime_type = file.content_type
    if not detected_mime_type or detected_mime_type == "application/octet-stream":
        # Try to detect from filename
        guessed_type, _ = mimetypes.guess_type(file.filename)
        if guessed_type:
            detected_mime_type = guessed_type
        elif file.filename.lower().endswith(('.jpg', '.jpeg')):
            detected_mime_type = 'image/jpeg'
        elif file.filename.lower().endswith('.png'):
            detected_mime_type = 'image/png'
        elif file.filename.lower().endswith('.heic'):
            detected_mime_type = 'image/heic'
        elif file.filename.lower().endswith('.webp'):
            detected_mime_type = 'image/webp'
        elif file.filename.lower().endswith('.avif'):
            detected_mime_type = 'image/avif'
        else:
            # Default to jpeg if we can't detect
            detected_mime_type = 'image/jpeg'
    
    try:
        # Create photo record FIRST to get the photo_id
        photo = Photo(
            user_id=current_user.user_id,
            filename=file.filename,
            mime_type=detected_mime_type,
            size_bytes=len(file_content),
            sha256=sha256_hash,
            uploaded_at=datetime.utcnow()
        )
        
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        
        # Now upload to B2 using the photo_id (so download can find it)
        b2_key = f"uploads/{current_user.user_id}/{photo.photo_id}/original/{file.filename}"
        
        try:
            b2_result = b2_service.upload_file(
                local_path=temp_path,
                b2_key=b2_key,
                content_type=file.content_type or "application/octet-stream"
            )
        except Exception as b2_error:
            # B2 upload failed - rollback the DB record
            await db.delete(photo)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to storage: {str(b2_error)}"
            )
        
        # Update user storage
        current_user.storage_used_bytes += len(file_content)
        await db.commit()
        
        return ConfirmResponse(
            photo_id=str(photo.photo_id),
            status="completed"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        print(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.delete("/cleanup/orphaned")
async def cleanup_orphaned_photos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dry_run: bool = True  # SAFE: dry-run by default
):
    """
    Check for orphaned photo records (DB records without B2 files).
    Set dry_run=false query param to actually delete.
    """
    # Get all user's photos
    result = await db.execute(
        select(Photo).where(
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
    )
    photos = result.scalars().all()
    
    orphaned_photos = []
    
    for photo in photos:
        b2_key = f"uploads/{current_user.user_id}/{photo.photo_id}/original/{photo.filename}"
        
        try:
            # Try to download first few bytes to verify file exists
            file_bytes = b2_service.download_file_bytes(b2_key)
            # File exists, not orphaned
        except Exception as e:
            # File doesn't exist or error - likely orphaned
            orphaned_photos.append({
                "photo_id": str(photo.photo_id),
                "filename": photo.filename,
                "error": str(e)
            })
            
            if not dry_run:
                await db.delete(photo)
    
    if not dry_run:
        await db.commit()
    
    return {
        "dry_run": dry_run,
        "orphaned_count": len(orphaned_photos),
        "orphaned_photos": orphaned_photos,
        "message": f"{'Would delete' if dry_run else 'Deleted'} {len(orphaned_photos)} orphaned records"
    }
