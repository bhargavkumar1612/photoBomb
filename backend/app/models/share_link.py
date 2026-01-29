"""
ShareLink model for sharing albums via secure links.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.config import settings

class ShareLink(Base):
    """ShareLink model for public sharing of albums"""
    __tablename__ = "share_links"
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    album_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.albums.album_id', ondelete='CASCADE'), nullable=False, index=True)
    
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
    views_detail = relationship("ShareLinkView", back_populates="share_link", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ShareLink {self.token} for Album {self.album_id}>"

class ShareLinkView(Base):
    """Model to track individual views of shared links"""
    __tablename__ = "share_link_views"
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    share_link_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.share_links.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.users.user_id', ondelete='SET NULL'), nullable=True) # If viewer is logged in
    
    # Optional: track IP hash or similar for anon views, but strictly user_id requested for "Who viewed"
    ip_hash = Column(String(64), nullable=True) 
    
    viewed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    share_link = relationship("ShareLink", back_populates="views_detail")
    user = relationship("User") # To show who viewed
