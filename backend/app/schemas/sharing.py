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

class ShareLinkResponse(ShareLinkBase):
    id: UUID
    album_id: UUID
    token: str
    views: int
    created_at: datetime
    share_url: Optional[str] = None # Helper field for frontend

    class Config:
        from_attributes = True

class SharedAlbumView(BaseModel):
    """Schema for public view of an album"""
    album_name: str
    album_description: Optional[str]
    owner_name: str
    photos: List[dict] # Simplified photo objects with signed URLs
