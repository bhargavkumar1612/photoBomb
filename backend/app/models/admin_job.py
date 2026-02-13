from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, TIMESTAMP, Text, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base
from app.core.config import settings

class AdminJob(Base):
    """Tracks admin maintenance jobs (clustering, re-scanning, etc.)"""
    __tablename__ = "admin_jobs"
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.users.user_id", ondelete="SET NULL"), nullable=True)
    
    job_type = Column(String(50), nullable=False)  # 'cluster', 'rescan', etc.
    status = Column(String(20), nullable=False, default='pending')  # pending, running, completed, failed
    
    # Job parameters
    target_user_ids = Column(JSON, nullable=False)  # List of user IDs
    scopes = Column(JSON, nullable=False)  # ['faces', 'animals', 'hashtags']
    force_reset = Column(Boolean, default=False)
    
    # Progress tracking
    progress_current = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    message = Column(Text, nullable=True)  # Current status message
    error = Column(Text, nullable=True)  # Error message if failed
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    __table_args__ = (
        Index('idx_admin_jobs_status', 'status'),
        Index('idx_admin_jobs_created', 'created_at'),
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<AdminJob {self.job_id} [{self.status}]>"
