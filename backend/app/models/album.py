"""
Album model for organizing photos into collections.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Table, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.config import settings

# Association table for many-to-many relationship between albums and photos
album_photos = Table(
    'album_photos',
    Base.metadata,
    Column('album_id', UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.albums.album_id', ondelete='CASCADE'), primary_key=True),
    Column('photo_id', UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.photos.photo_id', ondelete='CASCADE'), primary_key=True, index=True),
    Column('added_at', DateTime, default=datetime.utcnow),
    schema=settings.DB_SCHEMA
)

# Association table for album contributors
album_contributors = Table(
    'album_contributors',
    Base.metadata,
    Column('album_id', UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.albums.album_id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.users.user_id', ondelete='CASCADE'), primary_key=True),
    Column('role', String(50), default='contributor'), # contributor, viewer, admin
    Column('joined_at', DateTime, default=datetime.utcnow),
    schema=settings.DB_SCHEMA
)


class Album(Base):
    """Album model for photo collections"""
    __tablename__ = "albums"
    album_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_albums_user_updated', 'user_id', 'updated_at'),
        {'schema': settings.DB_SCHEMA}
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cover_photo_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.photos.photo_id', ondelete='SET NULL'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="albums")
    photos = relationship("Photo", secondary=album_photos, back_populates="albums")
    contributors = relationship("User", secondary=album_contributors, back_populates="shared_albums")
    cover_photo = relationship("Photo", foreign_keys=[cover_photo_id])
    share_links = relationship("ShareLink", back_populates="album", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Album {self.name} ({self.album_id})>"