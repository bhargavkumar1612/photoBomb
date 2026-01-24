from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select
from typing import List
import secrets
from datetime import datetime

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.album import Album
from app.models.photo import Photo
from app.models.share_link import ShareLink
from app.schemas.sharing import ShareLinkCreate, ShareLinkResponse, SharedAlbumView
from app.services.storage_factory import get_storage_service
from app.core.config import settings

router = APIRouter()

@router.post("/albums/{album_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    album_id: str,
    share_data: ShareLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new share link for an album"""
    # Verify ownership
    result = await db.execute(
        select(Album).where(Album.album_id == album_id, Album.user_id == current_user.user_id)
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    
    new_share = ShareLink(
        album_id=album.album_id,
        token=token,
        is_public=share_data.is_public,
        expires_at=share_data.expires_at,
        allowed_emails=share_data.allowed_emails
    )
    
    db.add(new_share)
    await db.commit()
    await db.refresh(new_share)
    return new_share

@router.get("/albums/{album_id}/share", response_model=List[ShareLinkResponse])
async def get_album_share_links(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all share links for an album"""
    result = await db.execute(
        select(Album)
        .options(selectinload(Album.share_links))
        .where(Album.album_id == album_id, Album.user_id == current_user.user_id)
    )
    album = result.scalar_one_or_none()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
        
    return album.share_links

@router.delete("/share/{token}")
async def revoke_share_link(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a share link"""
    # Join with Album to check user ownership
    result = await db.execute(
        select(ShareLink)
        .join(Album)
        .where(ShareLink.token == token, Album.user_id == current_user.user_id)
    )
    share = result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
        
    await db.delete(share)
    await db.commit()
    return {"message": "Share link revoked"}

@router.get("/shared/{token}", response_model=SharedAlbumView)
async def view_shared_album(
    token: str,
    db: Session = Depends(get_db)
):
    """Public endpoint to view a shared album"""
    result = await db.execute(
        select(ShareLink)
        .options(
            selectinload(ShareLink.album).selectinload(Album.photos)
        )
        .where(ShareLink.token == token)
    )
    share = result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(status_code=404, detail="Link invalid or expired")
        
    # Check expiry
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link expired")
        
    # Increment views
    share.views += 1
    await db.commit()
    
    # Get Album details
    album = share.album
    
    # Get Owner details
    result_owner = await db.execute(select(User).where(User.user_id == album.user_id))
    owner = result_owner.scalar_one_or_none()
    
    if not owner:
        # Should technically not happen if FK integrity holds, but good safety
        owner_name = "Unknown"
        # Can't generate valid URLs if we don't know the user_id prefix, but we have album.user_id
        owner_user_id = album.user_id
    else:
        owner_name = owner.full_name
        owner_user_id = owner.user_id

    # Generate Signed URLs
    storage = get_storage_service()
    
    def sign_b2_url(key: str) -> str:
        return storage.generate_presigned_url(key, expires_in=86400)

    # Process photos with Signed URLs
    photo_list = []
    for photo in album.photos:
        key_base = f"uploads/{owner_user_id}/{photo.photo_id}"

        # Generate signed URLs manually using the batch token
        thumb_urls = {
            "small": sign_b2_url(f"{key_base}/thumbnails/thumb_256.jpg"),
            "medium": sign_b2_url(f"{key_base}/thumbnails/thumb_512.jpg"),
            "original": sign_b2_url(f"{key_base}/original/{photo.filename}")
        }
        
        photo_list.append({
            "photo_id": str(photo.photo_id),
            "filename": photo.filename,
            "thumb_urls": thumb_urls,
            "taken_at": photo.taken_at,
            # photo.width/height not directly available on Photo model, skipping for now
            # "width": photo.width,
            # "height": photo.height
        })
        
    return {
        "album_name": album.name,
        "album_description": album.description,
        "owner_name": owner_name,
        "photos": photo_list
    }
