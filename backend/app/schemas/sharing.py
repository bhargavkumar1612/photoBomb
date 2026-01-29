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
    owner: Optional[PhotoOwnerInfo] = None

class SharedAlbumView(BaseModel):
    """Schema for public view of an album"""
    album_name: str
    album_description: Optional[str]
    owner_name: str
    photos: List[PhotoForSharedView]
