"""
Pipeline service for managing pipeline and task status updates.
Provides helper functions for worker tasks to update progress and metrics.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.pipeline import Pipeline, PipelineTask
import logging

logger = logging.getLogger(__name__)


async def update_pipeline_task_status(
    pipeline_id: str,
    photo_id: str,
    status: str,
    celery_task_id: Optional[str] = None,
    started_at: Optional[datetime] = None
) -> None:
    """
    Update pipeline task status.
    
    Args:
        pipeline_id: Pipeline UUID
        photo_id: Photo UUID
        status: New status ('running', 'completed', 'failed', etc.)
        celery_task_id: Celery task ID for cancellation
        started_at: Task start timestamp
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PipelineTask).where(
                    PipelineTask.pipeline_id == pipeline_id,
                    PipelineTask.photo_id == photo_id
                )
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = status
                if celery_task_id:
                    task.celery_task_id = celery_task_id
                if started_at:
                    task.started_at = started_at
                await db.commit()
                logger.info(f"Updated task {task.task_id} status to {status}")
            else:
                logger.warning(f"Pipeline task not found: pipeline={pipeline_id}, photo={photo_id}")
    except Exception as e:
        logger.error(f"Error updating pipeline task status: {e}")


async def update_pipeline_task_complete(
    pipeline_id: str,
    photo_id: str,
    status: str,
    total_time_ms: int,
    **metrics
) -> None:
    """
    Update pipeline task with completion metrics.
    
    Args:
        pipeline_id: Pipeline UUID
        photo_id: Photo UUID
        status: Final status ('completed', 'failed')
        total_time_ms: Total processing time in milliseconds
        **metrics: Additional metrics (download_time_ms, thumbnail_time_ms, etc.)
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PipelineTask).where(
                    PipelineTask.pipeline_id == pipeline_id,
                    PipelineTask.photo_id == photo_id
                )
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = status
                task.completed_at = datetime.utcnow()
                task.total_time_ms = total_time_ms
                
                # Update component metrics
                for key, value in metrics.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                
                await db.commit()
                logger.info(f"Completed task {task.task_id} in {total_time_ms}ms")
            else:
                logger.warning(f"Pipeline task not found: pipeline={pipeline_id}, photo={photo_id}")
    except Exception as e:
        logger.error(f"Error updating pipeline task completion: {e}")


async def update_pipeline_task_error(
    pipeline_id: str,
    photo_id: str,
    error_message: str,
    error_type: Optional[str] = None
) -> None:
    """
    Update pipeline task with error information.
    
    Args:
        pipeline_id: Pipeline UUID
        photo_id: Photo UUID
        error_message: Error description
        error_type: Error category ('download_failed', 'processing_error', etc.)
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PipelineTask).where(
                    PipelineTask.pipeline_id == pipeline_id,
                    PipelineTask.photo_id == photo_id
                )
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = 'failed'
                task.error_message = error_message
                task.error_type = error_type
                task.completed_at = datetime.utcnow()
                task.retry_count += 1
                
                await db.commit()
                logger.error(f"Task {task.task_id} failed: {error_message}")
            else:
                logger.warning(f"Pipeline task not found: pipeline={pipeline_id}, photo={photo_id}")
    except Exception as e:
        logger.error(f"Error updating pipeline task error: {e}")


async def update_pipeline_progress(pipeline_id: str) -> None:
    """
    Recalculate pipeline progress from tasks.
    Updates completed/failed/skipped counts and average processing time.
    Marks pipeline as completed when all tasks are done.
    
    Args:
        pipeline_id: Pipeline UUID
    """
    try:
        async with AsyncSessionLocal() as db:
            # Count task statuses
            result = await db.execute(
                select(
                    PipelineTask.status,
                    func.count(PipelineTask.task_id)
                )
                .where(PipelineTask.pipeline_id == pipeline_id)
                .group_by(PipelineTask.status)
            )
            
            status_counts = {row[0]: row[1] for row in result}
            
            # Get pipeline
            pipeline_result = await db.execute(
                select(Pipeline).where(Pipeline.pipeline_id == pipeline_id)
            )
            pipeline = pipeline_result.scalar_one_or_none()
            
            if not pipeline:
                logger.warning(f"Pipeline not found: {pipeline_id}")
                return
            
            # Update counts
            pipeline.completed_photos = status_counts.get('completed', 0)
            pipeline.failed_photos = status_counts.get('failed', 0)
            pipeline.skipped_photos = status_counts.get('skipped', 0)
            
            # Calculate average processing time
            avg_result = await db.execute(
                select(func.avg(PipelineTask.total_time_ms))
                .where(
                    PipelineTask.pipeline_id == pipeline_id,
                    PipelineTask.status == 'completed',
                    PipelineTask.total_time_ms.isnot(None)
                )
            )
            avg_time = avg_result.scalar()
            if avg_time:
                pipeline.avg_processing_time_ms = int(avg_time)
            
            # Calculate total processing time
            total_result = await db.execute(
                select(func.sum(PipelineTask.total_time_ms))
                .where(
                    PipelineTask.pipeline_id == pipeline_id,
                    PipelineTask.total_time_ms.isnot(None)
                )
            )
            total_time = total_result.scalar()
            if total_time:
                pipeline.total_processing_time_ms = int(total_time)
            
            # Check if pipeline is complete
            total = pipeline.total_photos
            processed = pipeline.completed_photos + pipeline.failed_photos + pipeline.skipped_photos
            
            if total > 0 and processed >= total:
                pipeline.status = 'completed'
                pipeline.completed_at = datetime.utcnow()
                logger.info(f"Pipeline {pipeline_id} completed: {pipeline.completed_photos} succeeded, {pipeline.failed_photos} failed")
            
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error updating pipeline progress: {e}")


async def create_pipeline_with_tasks(
    user_id: str,
    pipeline_type: str,
    photo_ids: list,
    photo_filenames: dict,
    name: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new pipeline with associated tasks.
    
    Args:
        user_id: User UUID
        pipeline_type: Type of pipeline ('upload', 'rescan', 'batch_analysis')
        photo_ids: List of photo UUIDs to process
        photo_filenames: Dict mapping photo_id to filename
        name: Pipeline name
        description: Pipeline description
        config: Pipeline configuration
        
    Returns:
        Pipeline UUID
    """
    try:
        async with AsyncSessionLocal() as db:
            # Create pipeline
            pipeline = Pipeline(
                user_id=user_id,
                pipeline_type=pipeline_type,
                name=name,
                description=description,
                status='running',
                total_photos=len(photo_ids),
                config=config,
                started_at=datetime.utcnow()
            )
            db.add(pipeline)
            await db.flush()
            
            # Create tasks
            for photo_id in photo_ids:
                task = PipelineTask(
                    pipeline_id=pipeline.pipeline_id,
                    photo_id=photo_id,
                    photo_filename=photo_filenames.get(str(photo_id), 'unknown'),
                    status='queued'
                )
                db.add(task)
            
            await db.commit()
            logger.info(f"Created pipeline {pipeline.pipeline_id} with {len(photo_ids)} tasks")
            
            return str(pipeline.pipeline_id)
            
    except Exception as e:
        logger.error(f"Error creating pipeline: {e}")
        raise


async def cancel_pipeline(pipeline_id: str) -> None:
    """
    Cancel a running pipeline and all its tasks.
    Revokes Celery tasks that are pending or running.
    
    Args:
        pipeline_id: Pipeline UUID
    """
    try:
        from app.celery_app import celery_app
        
        async with AsyncSessionLocal() as db:
            # Get pipeline
            pipeline_result = await db.execute(
                select(Pipeline).where(Pipeline.pipeline_id == pipeline_id)
            )
            pipeline = pipeline_result.scalar_one_or_none()
            
            if not pipeline:
                logger.warning(f"Pipeline not found: {pipeline_id}")
                return
            
            if pipeline.status in ['completed', 'cancelled']:
                logger.info(f"Pipeline {pipeline_id} already {pipeline.status}")
                return
            
            # Get all pending/running tasks
            tasks_result = await db.execute(
                select(PipelineTask)
                .where(PipelineTask.pipeline_id == pipeline_id)
                .where(PipelineTask.status.in_(['pending', 'queued', 'running']))
            )
            tasks = tasks_result.scalars().all()
            
            # Revoke Celery tasks
            for task in tasks:
                if task.celery_task_id:
                    celery_app.control.revoke(task.celery_task_id, terminate=True)
                    logger.info(f"Revoked Celery task {task.celery_task_id}")
                task.status = 'cancelled'
            
            # Update pipeline
            pipeline.status = 'cancelled'
            pipeline.cancelled_at = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Cancelled pipeline {pipeline_id}")
            
    except Exception as e:
        logger.error(f"Error cancelling pipeline: {e}")
        raise
