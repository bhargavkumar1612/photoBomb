
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, TIMESTAMP, func, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = {"schema": "photobomb"}

    tag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50), nullable=True) # e.g., 'animal', 'place', 'document' - helpful for UI grouping
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    photo_tags = relationship("PhotoTag", back_populates="tag", cascade="all, delete-orphan")


class PhotoTag(Base):
    __tablename__ = "photo_tags"
    __table_args__ = (
        PrimaryKeyConstraint('photo_id', 'tag_id'),
        {"schema": "photobomb"}
    )
    
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photobomb.photos.photo_id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("photobomb.tags.tag_id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, nullable=False) # 0.0 to 1.0
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("app.models.photo.Photo", backref="tags") # Use string for lazy load references or imports
    tag = relationship("Tag", back_populates="photo_tags")
