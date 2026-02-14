"""
Pipeline and PipelineTask models for tracking batch photo processing jobs.
Extends the former AdminJob model with enhanced progress tracking and metrics.
"""
from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, TIMESTAMP, Text, Index, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base
from app.core.config import settings


class Pipeline(Base):
    """
    Tracks batch photo processing pipelines (uploads, rescans, batch analysis).
    Formerly AdminJob - extended with enhanced metrics and progress tracking.
    """
    __tablename__ = "pipelines"
    
    pipeline_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.users.user_id", ondelete="SET NULL"), nullable=True)
    
    # Pipeline metadata
    pipeline_type = Column(String(50), nullable=False)  
    # 'upload', 'rescan', 'batch_analysis', 'admin_cluster', 'admin_rescan'
    name = Column(String(200), nullable=True)  # User-friendly name
    description = Column(Text, nullable=True)
    
    # Legacy fields (for backward compatibility with AdminJob)
    job_type = Column(String(50), nullable=True)  # Legacy: 'cluster', 'rescan'
    target_user_ids = Column(JSON, nullable=True)  # Legacy admin jobs
    scopes = Column(JSON, nullable=True)  # Legacy: ['faces', 'animals', 'hashtags']
    force_reset = Column(Boolean, default=False)  # Legacy
    
    # Status tracking
    status = Column(String(20), nullable=False, default='pending')  
    # pending, queued, running, paused, completed, failed, cancelled
    
    # Progress metrics
    total_photos = Column(Integer, default=0)
    completed_photos = Column(Integer, default=0)
    failed_photos = Column(Integer, default=0)
    skipped_photos = Column(Integer, default=0)
    
    # Performance metrics
    avg_processing_time_ms = Column(Integer, nullable=True)  # Average per photo
    total_processing_time_ms = Column(BigInteger, default=0)
    
    # Configuration
    config = Column(JSON, nullable=True)  # Pipeline-specific settings
    # Example: {'scopes': ['faces', 'animals', 'tags'], 'force_reprocess': false}
    
    # Error tracking
    error = Column(Text, nullable=True)  # Error message if failed
    message = Column(Text, nullable=True)  # Current status message
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    cancelled_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    tasks = relationship("PipelineTask", back_populates="pipeline", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_pipelines_user_status', 'user_id', 'status'),
        Index('idx_pipelines_status', 'status'),
        Index('idx_pipelines_created', 'created_at'),
        Index('idx_pipelines_type', 'pipeline_type'),
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<Pipeline {self.pipeline_id} [{self.status}]>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_photos == 0:
            return 0.0
        processed = self.completed_photos + self.failed_photos + self.skipped_photos
        return (processed / self.total_photos) * 100
    
    @property
    def estimated_time_remaining_ms(self) -> int:
        """Estimate time remaining based on average processing time"""
        if not self.avg_processing_time_ms or self.total_photos == 0:
            return 0
        remaining = self.total_photos - (self.completed_photos + self.failed_photos + self.skipped_photos)
        return remaining * self.avg_processing_time_ms


class PipelineTask(Base):
    """Individual photo processing task within a pipeline"""
    __tablename__ = "pipeline_tasks"
    
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.pipelines.pipeline_id", ondelete="CASCADE"), nullable=False)
    photo_id = Column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.photos.photo_id", ondelete="CASCADE"), nullable=False)
    
    # Task metadata
    photo_filename = Column(String(500), nullable=False)  # Cached for display
    celery_task_id = Column(String(255), nullable=True)  # Celery task ID for cancellation
    
    # Status
    status = Column(String(20), nullable=False, default='pending')
    # pending, queued, running, completed, failed, cancelled, skipped
    
    # Performance metrics (in milliseconds)
    total_time_ms = Column(Integer, nullable=True)
    download_time_ms = Column(Integer, nullable=True)
    thumbnail_time_ms = Column(Integer, nullable=True)
    face_detection_time_ms = Column(Integer, nullable=True)
    animal_detection_time_ms = Column(Integer, nullable=True)
    classification_time_ms = Column(Integer, nullable=True)
    ocr_time_ms = Column(Integer, nullable=True)
    db_write_time_ms = Column(Integer, nullable=True)
    
    # Component results
    faces_detected = Column(Integer, default=0)
    animals_detected = Column(Integer, default=0)
    tags_created = Column(Integer, default=0)
    text_words_extracted = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)  # 'download_failed', 'processing_error', etc.
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    pipeline = relationship("Pipeline", back_populates="tasks")
    photo = relationship("Photo")
    
    __table_args__ = (
        Index('idx_pipeline_tasks_pipeline', 'pipeline_id'),
        Index('idx_pipeline_tasks_status', 'pipeline_id', 'status'),
        Index('idx_pipeline_tasks_photo', 'photo_id'),
        Index('idx_pipeline_tasks_celery', 'celery_task_id'),
        {'schema': settings.DB_SCHEMA}
    )
    
    def __repr__(self):
        return f"<PipelineTask {self.task_id} [{self.status}]>"


# Backward compatibility alias
AdminJob = Pipeline
