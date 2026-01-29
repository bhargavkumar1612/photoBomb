from sqlalchemy import Column, String, ForeignKey, Integer, Float, Boolean, TIMESTAMP, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base
from app.core.config import settings

class Animal(Base):
    """
    Represents a unique animal (e.g., a specific pet) identified across multiple photos.
    """
    __tablename__ = "animals"
    
    animal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.users.user_id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=True)  # User assigned name, e.g., "Buddy"
    
    # Pointer to a specific AnimalDetection to use as the cover/thumbnail
    cover_detection_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.animal_detections.detection_id", ondelete="SET NULL", use_alter=True), nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    detections = relationship("AnimalDetection", back_populates="animal", foreign_keys="[AnimalDetection.animal_id]")
    cover_detection = relationship("AnimalDetection", foreign_keys=[cover_detection_id], post_update=True)
    
    __table_args__ = (
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<Animal {self.name or self.animal_id}>"


class AnimalDetection(Base):
    """
    Represents a detected animal in a specific photo.
    """
    __tablename__ = "animal_detections"
    
    detection_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.photos.photo_id", ondelete="CASCADE"), nullable=False)
    
    # Which animal group this detection belongs to
    animal_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.animals.animal_id", ondelete="SET NULL"), nullable=True)
    
    # Label from object detector (e.g. 'dog', 'cat')
    label = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Visual embedding (512-d CLIP vector) for clustering/recognition
    embedding = Column(Vector(512))
    
    # Bounding Box (Top, Right, Bottom, Left) - absolute or normalized? 
    # Let's stick to absolute pixels for consistency with Face model
    location_top = Column(Integer, nullable=False)
    location_right = Column(Integer, nullable=False)
    location_bottom = Column(Integer, nullable=False)
    location_left = Column(Integer, nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("Photo", backref="animal_detections")
    animal = relationship("Animal", back_populates="detections", foreign_keys=[animal_id])
    
    __table_args__ = (
        Index('idx_animal_detections_animal', 'animal_id'),
        Index('idx_animal_detections_photo', 'photo_id'),
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<AnimalDetection {self.label} in Photo {self.photo_id}>"
