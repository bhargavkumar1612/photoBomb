"""
SharedPhoto model for direct photo sharing and pending invites.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.core.config import settings

class SharedPhoto(Base):
    __tablename__ = "shared_photos"
    __table_args__ = (
        Index('idx_shared_photos_receiver', 'receiver_id'),
        Index('idx_shared_photos_email', 'target_email'),
        Index('idx_shared_photos_token', 'invite_token'),
        {'schema': settings.DB_SCHEMA}
    )

    share_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.photos.photo_id', ondelete='CASCADE'), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Receiver Logic (Either ID or Email+Token)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey(f'{settings.DB_SCHEMA}.users.user_id', ondelete='CASCADE'), nullable=True) 
    target_email = Column(String, nullable=True) # For pending shares
    invite_token = Column(String, unique=True, nullable=True) # For pending link
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    photo = relationship("Photo")
    owner = relationship("User", foreign_keys=[owner_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

    def __repr__(self):
        return f"<SharedPhoto {self.share_id} Owner={self.owner_id} Receiver={self.receiver_id or self.target_email}>"
