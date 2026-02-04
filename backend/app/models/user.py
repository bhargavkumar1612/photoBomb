"""
User model for authentication and account management.
"""
from sqlalchemy import Column, String, Boolean, BigInteger, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.core.config import settings


class User(Base):
    """User model with OAuth support and storage quota tracking."""
    
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'",
            name='email_format'
        ),
        {'schema': settings.DB_SCHEMA}
    )
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)  # NULL for OAuth-only users
    full_name = Column(String(255), nullable=False)
    
    # OAuth providers
    google_id = Column(String(255), unique=True, nullable=True)
    apple_id = Column(String(255), unique=True, nullable=True)
    
    # Privacy settings
    face_recognition_enabled = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Storage quota (bytes)
    storage_quota_bytes = Column(BigInteger, default=107374182400)  # 100 GB
    storage_used_bytes = Column(BigInteger, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    albums = relationship("Album", back_populates="user", cascade="all, delete-orphan")
    shared_albums = relationship("Album", secondary=f"{settings.DB_SCHEMA}.album_contributors", back_populates="contributors")
    
    def __repr__(self):
        return f"<User {self.email}>"