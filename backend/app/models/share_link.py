"""
ShareLink model for sharing albums via secure links.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base

class ShareLink(Base):
    """ShareLink model for public sharing of albums"""
    __tablename__ = "share_links"
    __table_args__ = {'schema': 'photobomb'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey('photobomb.albums.album_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # The secure token used in the URL
    token = Column(String(64), unique=True, nullable=False, index=True)
    
    # Configuration
    is_public = Column(Boolean, default=False) # If false, might require specific email match or password (future)
    expires_at = Column(DateTime, nullable=True)
    allowed_emails = Column(JSON, nullable=True) # List of allowed emails if restricted
    
    # Stats
    views = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    album = relationship("Album", back_populates="share_links")

    def __repr__(self):
        return f"<ShareLink {self.token} for Album {self.album_id}>"
