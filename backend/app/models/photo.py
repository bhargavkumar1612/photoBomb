"""
Photo model with EXIF metadata and deduplication support.
"""
from sqlalchemy import Column, String, BigInteger, Integer, Boolean, TIMESTAMP, Text, CheckConstraint, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Photo(Base):
    """Photo model with EXIF data and location support."""
    
    __tablename__ = "photos"
    
    photo_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("photobomb.users.user_id", ondelete="CASCADE"), nullable=False)
    
    # File metadata
    filename = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    
    # Storage Location
    # 'b2_native' (Legacy) or 's3' (R2/AWS)
    storage_provider = Column(String(20), default='b2_native', nullable=False)
    
    # Deduplication
    sha256 = Column(String(64), nullable=False, index=True)
    phash = Column(BigInteger, nullable=True, index=True)  # Perceptual hash
    
    # EXIF data
    taken_at = Column(TIMESTAMP(timezone=True), nullable=True)
    camera_make = Column(String(100), nullable=True)
    camera_model = Column(String(100), nullable=True)
    lens = Column(String(100), nullable=True)
    iso = Column(Integer, nullable=True)
    aperture = Column(String(20), nullable=True)
    shutter_speed = Column(String(20), nullable=True)
    focal_length = Column(String(20), nullable=True)
    
    # GPS
    gps_lat = Column(Numeric(10, 7), nullable=True)
    gps_lng = Column(Numeric(10, 7), nullable=True)
    gps_altitude = Column(Numeric(8, 2), nullable=True)
    location_name = Column(Text, nullable=True)  # Reverse-geocoded
    
    # User-editable fields
    caption = Column(Text, nullable=True)
    favorite = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    
    # Timestamps
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="photos")
    albums = relationship("Album", secondary="photobomb.album_photos", back_populates="photos")
    files = relationship("PhotoFile", back_populates="photo", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/heic', 'image/webp', 'image/avif')",
            name='valid_mime_type'
        ),
        Index('idx_photos_user_taken', 'user_id', 'taken_at', postgresql_where="deleted_at IS NULL"),
        Index('idx_photos_user_uploaded', 'user_id', 'uploaded_at', postgresql_where="deleted_at IS NULL"),
        Index('idx_photos_favorite', 'user_id', 'uploaded_at', postgresql_where="favorite = true AND deleted_at IS NULL"),
        Index('idx_photos_user_deleted', 'user_id', 'deleted_at', postgresql_where="deleted_at IS NOT NULL"),
        {'schema': 'photobomb'}
    )
    
    def __repr__(self):
        return f"<Photo {self.filename}>"


class PhotoFile(Base):
    """Photo file variants (originals + thumbnails)."""
    
    __tablename__ = "photo_files"
    
    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photobomb.photos.photo_id", ondelete="CASCADE"), nullable=False)
    
    variant = Column(String(50), nullable=False)  # 'original', 'thumb_256', etc.
    format = Column(String(10), nullable=False)  # 'jpeg', 'webp', 'avif'
    
    # Storage
    storage_backend = Column(String(20), default='b2')
    b2_bucket = Column(String(100), nullable=True)
    b2_key = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    
    # Dimensions
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("Photo", back_populates="files")
    
    __table_args__ = (
        Index('idx_photo_files_photo', 'photo_id'),
        Index('idx_photo_files_unique', 'photo_id', 'variant', 'format', unique=True),
        {'schema': 'photobomb'}
    )
    
    def __repr__(self):
        return f"<PhotoFile {self.variant}.{self.format}>"
