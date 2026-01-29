from sqlalchemy import Column, String, ForeignKey, Integer, Float, Boolean, TIMESTAMP, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base
from app.core.config import settings

class Person(Base):
    """
    Represents a unique person identified across multiple photos.
    """
    __tablename__ = "people"
    
    person_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.users.user_id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=True)  # User assigned name, e.g., "Alice"
    
    # Pointer to a specific Face to use as the cover/thumbnail for this person
    cover_face_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.faces.face_id", ondelete="SET NULL", use_alter=True), nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    # user = relationship("User", back_populates="people") # User needs to be updated to have back_populates if we want
    faces = relationship("Face", back_populates="person", foreign_keys="[Face.person_id]")
    cover_face = relationship("Face", foreign_keys=[cover_face_id], post_update=True)
    
    __table_args__ = (
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<Person {self.name or self.person_id}>"


class Face(Base):
    """
    Represents a detected face in a specific photo.
    """
    __tablename__ = "faces"
    
    face_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.photos.photo_id", ondelete="CASCADE"), nullable=False)
    
    # Which person this face belongs to (nullable if not yet clustered/assigned)
    person_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.people.person_id", ondelete="SET NULL"), nullable=True)
    
    # Face encoding vector (128 dimensions for dlib/face_recognition)
    encoding = Column(Vector(128))
    
    # Bounding Box (Top, Right, Bottom, Left)
    location_top = Column(Integer, nullable=False)
    location_right = Column(Integer, nullable=False)
    location_bottom = Column(Integer, nullable=False)
    location_left = Column(Integer, nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("Photo", backref="faces")
    person = relationship("Person", back_populates="faces", foreign_keys=[person_id])
    
    __table_args__ = (
        Index('idx_faces_person', 'person_id'),
        Index('idx_faces_photo', 'photo_id'),
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<Face {self.face_id} in Photo {self.photo_id}>"