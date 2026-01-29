from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func
from typing import List, Optional
import secrets
from datetime import datetime

from app.core.database import get_db
from app.api.auth import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.album import Album
from app.models.photo import Photo
from app.models.share_link import ShareLink, ShareLinkView
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
    """Get all share links for an album with usage stats"""
    # Use selectinload to load views_detail and the associated user for each view
    result = await db.execute(
        select(ShareLink)
        .options(
            selectinload(ShareLink.views_detail).selectinload(ShareLinkView.user)
        )
        .join(Album)
        .where(Album.album_id == album_id, Album.user_id == current_user.user_id)
    )
    share_links = result.scalars().all()
    
    # Map views_detail to viewers list for response
    for link in share_links:
        viewers_list = []
        # Group by user to show latest view? Or show all individual views?
        # User request: "who has seen my album". 
        # Listing unique users is probably better than a raw log.
        # Let's map unique users, taking the most recent 'viewed_at'
        
        seen_users = {}
        for view in link.views_detail:
            if view.user_id: # Only logged in users
                # If using eager loading, view.user should be available
                u = view.user
                if u:
                    if u.user_id not in seen_users or view.viewed_at > seen_users[u.user_id]['viewed_at']:
                        seen_users[u.user_id] = {
                            "user_id": u.user_id,
                            "full_name": u.full_name,
                            "viewed_at": view.viewed_at
                        }
        
        # Sort by viewed_at desc
        link.viewers = sorted(seen_users.values(), key=lambda x: x['viewed_at'], reverse=True)

    return share_links

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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Public endpoint to view a shared album"""
    result = await db.execute(
        select(ShareLink)
        .options(
            selectinload(ShareLink.album).selectinload(Album.photos).selectinload(Photo.user)
        )
        .where(ShareLink.token == token)
    )
    share = result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(status_code=404, detail="Link invalid or expired")
        
    # Check expiry
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link expired")
        
    # Record View safely
    try:
        view_entry = ShareLinkView(
            share_link_id=share.id,
            user_id=current_user.user_id if current_user else None,
            viewed_at=datetime.utcnow()
        )
        db.add(view_entry)
            
        # Increment aggregate counter
        share.views += 1
        await db.commit()
    except Exception as e:
        print(f"Failed to log view: {e}")
        # Identify failure but don't block response
        await db.rollback()
    
    # Get Album details
    album = share.album
    
    # Get Album Owner details
    result_owner = await db.execute(select(User).where(User.user_id == album.user_id))
    owner = result_owner.scalar_one_or_none()
    
    if not owner:
        owner_name = "Unknown"
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
    
    # For shared view permission check: if logged-in user is a contributor, frontend might show "Add" button
    # But this endpoint just returns photos.
    
    for photo in album.photos:
        # Photos store the user_id of uploader.
        uploader_id = photo.user_id
        
        # We need the uploader's name. We eagerly loaded Photo.user.
        uploader_name = photo.user.full_name if photo.user else "Unknown"
        uploader_avatar = None # photo.user.avatar_url if we had one
        
        key_base = f"uploads/{uploader_id}/{photo.photo_id}"

        # Generate signed URLs manually using the batch token
        thumb_urls = {
            "thumb_256": sign_b2_url(f"{key_base}/thumbnails/thumb_256.jpg"),
            "thumb_512": sign_b2_url(f"{key_base}/thumbnails/thumb_512.jpg"),
            "thumb_1024": sign_b2_url(f"{key_base}/thumbnails/thumb_1024.jpg"),
            "original": sign_b2_url(f"{key_base}/original/{photo.filename}")
        }
        
        photo_list.append({
            "photo_id": str(photo.photo_id),
            "filename": photo.filename,
            "thumb_urls": thumb_urls,
            "taken_at": photo.taken_at,
            "owner": {
                "user_id": str(uploader_id),
                "name": uploader_name
            }
        })
        
    return {
        "album_name": album.name,
        "album_description": album.description,
        "owner_name": owner_name,
        "photos": photo_list,
        # "can_add_photos": is_contributor # Future optimization
    }
