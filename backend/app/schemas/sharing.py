from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ShareLinkBase(BaseModel):
    is_public: bool = True
    expires_at: Optional[datetime] = None
    allowed_emails: Optional[List[str]] = None

class ShareLinkCreate(ShareLinkBase):
    pass

class ViewerInfo(BaseModel):
    user_id: Optional[UUID]
    full_name: Optional[str] = "Anonymous"
    viewed_at: datetime
    
    class Config:
        from_attributes = True

class ShareLinkResponse(ShareLinkBase):
    id: UUID
    album_id: UUID
    token: str
    views: int
    created_at: datetime
    share_url: Optional[str] = None # Helper field for frontend
    viewers: List[ViewerInfo] = []

    class Config:
        from_attributes = True

class PhotoOwnerInfo(BaseModel):
    user_id: str
    name: str

class PhotoForSharedView(BaseModel):
    photo_id: str
    filename: str
    thumb_urls: dict
    taken_at: Optional[datetime]
    uploaded_at: Optional[datetime] = None
    shared_at: Optional[datetime] = None
    owner: Optional[PhotoOwnerInfo] = None

class SharedAlbumView(BaseModel):
    """Schema for public view of an album"""
    album_name: str
    album_description: Optional[str]
    owner_name: str
    photos: List[PhotoForSharedView]

class SharePhotosRequest(BaseModel):
    photo_ids: List[str]
    target_email: str

class SharePhotosResponse(BaseModel):
    status: str # "shared" or "link"
    link: Optional[str] = None
    message: str

class ConnectionUser(BaseModel):
    user_id: Optional[UUID]
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class SharedAlbumSummary(BaseModel):
    album_id: str
    name: str
    photo_count: int
    cover_photo_url: Optional[str] = None
    created_at: datetime
    
class InboxItem(BaseModel):
    sender: ConnectionUser
    photo_count: int
    album_count: int = 0
    latest_share_date: datetime
    preview_thumbs: List[str] # List of signed URLs for preview
    photos: List[PhotoForSharedView] = []
    albums: List[SharedAlbumSummary] = []
