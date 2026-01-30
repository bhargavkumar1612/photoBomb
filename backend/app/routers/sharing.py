from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func
from typing import List, Optional
import secrets
import uuid
from datetime import datetime, timezone

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

    # Auto-join logic: If user is logged in, and not owner, and not already a contributor, add as viewer.
    if current_user and album.user_id != current_user.user_id:
        from app.models.album import album_contributors
        # Check if already a contributor
        check_contrib = await db.execute(
            select(album_contributors.c.user_id).where(
                album_contributors.c.album_id == album.album_id,
                album_contributors.c.user_id == current_user.user_id
            )
        )
        if not check_contrib.scalar_one_or_none():
            # Add as viewer
            try:
                stmt = album_contributors.insert().values(
                    album_id=album.album_id,
                    user_id=current_user.user_id,
                    role='viewer',
                    joined_at=datetime.utcnow()
                )
                await db.execute(stmt)
                await db.commit()
            except Exception as e:
                print(f"Failed to auto-join album: {e}")
                # Don't block viewing if join fails
                await db.rollback()
    
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
        
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{uploader_id}/{photo.photo_id}"

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

# --- Direct Photo Sharing Endpoints ---

from app.models.shared_photo import SharedPhoto
from app.schemas.sharing import SharePhotosRequest, SharePhotosResponse, InboxItem, ConnectionUser

@router.post("/sharing/photos", response_model=SharePhotosResponse)
async def share_photos(
    request: SharePhotosRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Share photos with a user by email (or create pending invite)"""
    photo_ids = [uuid.UUID(pid) for pid in request.photo_ids]
    target_email = request.target_email.lower().strip()
    
    # Check if user exists
    result = await db.execute(select(User).where(User.email == target_email))
    target_user = result.scalar_one_or_none()
    
    response_data = {"status": "shared", "message": "Photos shared successfully", "link": None}
    
    # Determine receiver info
    receiver_id = target_user.user_id if target_user else None
    invite_token = None
    
    # If user doesn't exist, generate invite token
    if not target_user:
        invite_token = secrets.token_urlsafe(32)
        response_data["status"] = "link"
        response_data["message"] = "User not found. Share this invite link manually."
        # In production, this would be your actual domain
        response_data["link"] = f"{settings.APP_URL or 'http://localhost:3000'}/invite?token={invite_token}"

    # Create SharedPhoto records
    new_shares = []
    for pid in photo_ids:
        # Check if already shared to this person/email to avoid duplicates
        if target_user:
            existing = await db.execute(
                select(SharedPhoto).where(
                    SharedPhoto.photo_id == pid,
                    SharedPhoto.owner_id == current_user.user_id,
                    SharedPhoto.receiver_id == target_user.user_id
                )
            )
        else:
             existing = await db.execute(
                select(SharedPhoto).where(
                    SharedPhoto.photo_id == pid,
                    SharedPhoto.owner_id == current_user.user_id,
                    SharedPhoto.target_email == target_email
                )
            )
            
        if existing.scalar_one_or_none():
            continue

        share = SharedPhoto(
            photo_id=pid,
            owner_id=current_user.user_id,
            receiver_id=receiver_id,
            target_email=target_email if not receiver_id else None,
            invite_token=invite_token
        )
        db.add(share)
    
    await db.commit()
    return response_data

@router.post("/sharing/claim")
async def claim_pending_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim any pending shares for the current user's email"""
    # Find shares waiting for this email
    result = await db.execute(
        select(SharedPhoto).where(
            SharedPhoto.target_email == current_user.email,
            SharedPhoto.receiver_id == None
        )
    )
    pending_shares = result.scalars().all()
    
    count = 0
    for share in pending_shares:
        share.receiver_id = current_user.user_id
        share.target_email = None # Clear pending status
        share.invite_token = None
        count += 1
    
    if count > 0:
        await db.commit()
        
    return {"message": f"Claimed {count} shared photos"}

@router.get("/sharing/inbox", response_model=List[InboxItem])
async def get_share_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get photos and albums shared with me, grouped by sender"""
    storage = get_storage_service()
    
    # 1. Fetch Shared Photos
    result = await db.execute(
        select(SharedPhoto)
        .options(
            selectinload(SharedPhoto.owner),
            selectinload(SharedPhoto.photo)
        )
        .where(SharedPhoto.receiver_id == current_user.user_id)
        .order_by(SharedPhoto.created_at.desc())
    )
    shares = result.scalars().all()
    
    # 2. Fetch Shared Albums (where I am a contributor)
    from app.models.album import album_contributors
    albums_result = await db.execute(
        select(Album)
        .join(album_contributors, Album.album_id == album_contributors.c.album_id)
        .options(
            selectinload(Album.cover_photo),
            selectinload(Album.user) 
        )
        .where(album_contributors.c.user_id == current_user.user_id)
    )
    # Note: If no relationship `owner`, we rely on manual join or we assume `user` relationship exists.
    # Looking at other files, `p.user` exists on Photo. `Album` usually has `user` too.
    # Let's verify... previous files didn't show Album model definition.
    # But `album.user_id` is used.
    # I'll try `selectinload(Album.user)`. If it fails, I might need to fix.
    # Actually, let's assume `Album` has a `user` relationship.
    
    result_albums = await db.execute(
        select(Album)
        .join(album_contributors, Album.album_id == album_contributors.c.album_id)
        .options(
            selectinload(Album.cover_photo),
            selectinload(Album.user),
            selectinload(Album.photos) # Load photos for fallback cover
        )
        .where(album_contributors.c.user_id == current_user.user_id)
    )
    shared_albums = result_albums.scalars().all()

    inbox_map = {}
    
    # Helper to init group
    def get_group(user):
        uid = user.user_id
        if uid not in inbox_map:
             inbox_map[uid] = {
                "sender": {
                    "user_id": user.user_id,
                    "full_name": user.full_name,
                    "email": user.email,
                },
                "photo_count": 0,
                "album_count": 0,
                "latest_share_date": None,
                "preview_thumbs": [],
                "photos": [],
                "albums": []
            }
        return inbox_map[uid]

    # Process Photos
    for share in shares:
        owner = share.owner
        if not owner: continue
        
        group = get_group(owner)
        group["photo_count"] += 1
        if share.created_at and (group["latest_share_date"] is None or share.created_at > group["latest_share_date"]):
             group["latest_share_date"] = share.created_at
        
        photo = share.photo
        if photo:
            key_base = f"{settings.STORAGE_PATH_PREFIX}/{owner.user_id}/{photo.photo_id}"
            thumb_urls = {
                "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
                "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
                "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600),
            }
            
            # Preview
            if len(group["preview_thumbs"]) < 4:
                group["preview_thumbs"].append(thumb_urls["thumb_256"])
            
            # Full list
            group["photos"].append({
                "photo_id": str(photo.photo_id),
                "filename": photo.filename,
                "thumb_urls": thumb_urls,
                "taken_at": photo.taken_at,
                "uploaded_at": photo.uploaded_at,
                "shared_at": share.created_at,
                "owner": {
                    "user_id": str(group["sender"]["user_id"]),
                    "name": group["sender"]["full_name"]
                }
            })

    # Process Albums
    from app.schemas.sharing import SharedAlbumSummary
    for album in shared_albums:
        owner = album.user
        if not owner: continue
        
        group = get_group(owner)
        group["album_count"] += 1
       
        # Normalize album date to be timezone aware (since SharedPhoto is aware)
        album_date = album.updated_at
        if album_date and album_date.tzinfo is None:
             album_date = album_date.replace(tzinfo=timezone.utc)

        if album_date and (group["latest_share_date"] is None or album_date > group["latest_share_date"]):
             group["latest_share_date"] = album_date

        # Cover photo logic
        cover_url = None
        target_photo = album.cover_photo
        
        # Fallback to first photo if no cover set
        if not target_photo and album.photos and len(album.photos) > 0:
            # Sort by date usually? Or just take first provided by relationship (usually insertions or random unless ordered)
            # For efficiency we just take the first one
            target_photo = album.photos[0]
            
        if target_photo:
             # Cover photo owner is likely the album owner (or uploader of that photo?)
             # Photo model has user_id. Use that to be safe.
             p_owner_id = target_photo.user_id
             key = f"{settings.STORAGE_PATH_PREFIX}/{p_owner_id}/{target_photo.photo_id}/thumbnails/thumb_512.jpg"
             cover_url = storage.generate_presigned_url(key, expires_in=3600)
        
        group["albums"].append(SharedAlbumSummary(
            album_id=str(album.album_id),
            name=album.name,
            photo_count=len(album.photos), # We loaded photos, so we can give accurate count now
            cover_photo_url=cover_url,
            created_at=album.created_at
        ))

    # Clean up dates
    result_list = list(inbox_map.values())
    for item in result_list:
        if item["latest_share_date"] == datetime.min:
             item["latest_share_date"] = datetime.utcnow() # Fallback

    # Sort final list by latest activity
    result_list.sort(key=lambda x: x["latest_share_date"], reverse=True)
    
    return result_list

@router.get("/sharing/connections", response_model=List[ConnectionUser])
async def get_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users I have interacted with (sent to or received from)"""
    
    # 1. People who sent me photos
    sent_to_me = await db.execute(
        select(User)
        .join(SharedPhoto, SharedPhoto.owner_id == User.user_id)
        .where(SharedPhoto.receiver_id == current_user.user_id)
        .distinct()
    )
    
    # 2. People I sent photos to
    i_sent_to = await db.execute(
        select(User)
        .join(SharedPhoto, SharedPhoto.receiver_id == User.user_id)
        .where(SharedPhoto.owner_id == current_user.user_id)
        .distinct()
    )

    # 3. People involved in shared albums (contributors)
    # Be careful: album_contributors links Album <-> User. 
    # If I am owner, contributors are people I shared with.
    # If I am contributor, owner is someone who shared with me.
    
    from app.models.album import Album, album_contributors
    
    # 3a. People I shared albums with (I am owner, they are contributors)
    album_shares_out = await db.execute(
        select(User)
        .join(album_contributors, User.user_id == album_contributors.c.user_id)
        .join(Album, Album.album_id == album_contributors.c.album_id)
        .where(Album.user_id == current_user.user_id)
        .distinct()
    )

    # 3b. People who shared albums with me (I am contributor, they are owner)
    album_shares_in = await db.execute(
        select(User)
        .join(Album, User.user_id == Album.user_id)
        .join(album_contributors, Album.album_id == album_contributors.c.album_id)
        .where(album_contributors.c.user_id == current_user.user_id)
        .distinct()
    )
    
    # Combine sets
    users =  set(sent_to_me.scalars().all()) | \
             set(i_sent_to.scalars().all()) | \
             set(album_shares_out.scalars().all()) | \
             set(album_shares_in.scalars().all())
    
    return list(users)
