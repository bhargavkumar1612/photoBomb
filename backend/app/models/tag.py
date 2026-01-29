
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, TIMESTAMP, func, UniqueConstraint, PrimaryKeyConstraint, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.config import settings

class Tag(Base):
    __tablename__ = "tags"
    tag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=True) # e.g., 'animal', 'place', 'document' - helpful for UI grouping
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_tags_category', 'category'),
        {"schema": settings.DB_SCHEMA}
    )
    
    # Relationships
    photo_tags = relationship("PhotoTag", back_populates="tag", cascade="all, delete-orphan", overlaps="photos_list,visual_tags")


class PhotoTag(Base):
    __tablename__ = "photo_tags"
    __table_args__ = (
        PrimaryKeyConstraint('photo_id', 'tag_id'),
        Index('idx_photo_tags_tag_id', 'tag_id'),
        Index('idx_photo_tags_tag_confidence', 'tag_id', 'confidence'),
        {"schema": settings.DB_SCHEMA}
    )
    
    photo_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.photos.photo_id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.tags.tag_id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, nullable=False) # 0.0 to 1.0
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("app.models.photo.Photo", backref=backref("tags", overlaps="photos_list,visual_tags"), overlaps="photos_list,visual_tags") # Use string for lazy load references or imports
    tag = relationship("Tag", back_populates="photo_tags", overlaps="photos_list,visual_tags")