"""
Pipeline Management API Endpoints.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete, or_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineTask
from app.services.pipeline_service import cancel_pipeline, create_pipeline_with_tasks

router = APIRouter()


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------

class PipelineTaskResponse(BaseModel):
    task_id: UUID
    pipeline_id: UUID
    photo_id: UUID
    photo_filename: str
    status: str
    
    # Metrics
    total_time_ms: Optional[int]
    error_message: Optional[str]
    error_type: Optional[str]
    
    # Detailed timing
    download_time_ms: Optional[int]
    thumbnail_time_ms: Optional[int]
    face_detection_time_ms: Optional[int]
    animal_detection_time_ms: Optional[int]
    classification_time_ms: Optional[int]
    ocr_time_ms: Optional[int]
    db_write_time_ms: Optional[int]
    
    # Results
    faces_detected: int
    animals_detected: int
    tags_created: int
    text_words_extracted: int
    
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PipelineResponse(BaseModel):
    pipeline_id: UUID
    user_id: Optional[UUID]
    pipeline_type: str
    name: Optional[str]
    description: Optional[str]
    status: str
    
    # Progress
    total_photos: int
    completed_photos: int
    failed_photos: int
    skipped_photos: int
    progress_percentage: float
    estimated_time_remaining_ms: int
    
    # Performance
    avg_processing_time_ms: Optional[int]
    total_processing_time_ms: int
    
    error: Optional[str]
    
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PipelineListResponse(BaseModel):
    items: List[PipelineResponse]
    total: int
    page: int
    size: int


class CreatePipelineRequest(BaseModel):
    pipeline_type: str = Field(..., description="Type of pipeline: 'rescan', 'batch_analysis'")
    name: Optional[str] = None
    description: Optional[str] = None
    photo_ids: List[UUID]
    config: Optional[Dict[str, Any]] = None


class RerunPipelineRequest(BaseModel):
    failed_only: bool = True
    include_skipped: bool = False
    task_ids: Optional[List[UUID]] = None


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    page: int = Query(1, gt=0),
    size: int = Query(20, gt=0, le=100),
    status: Optional[str] = None,
    pipeline_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List pipelines with pagination and filtering."""
    offset = (page - 1) * size
    
    query = select(Pipeline).where(Pipeline.user_id == current_user.user_id)
    
    if status:
        query = query.where(Pipeline.status == status)
    if pipeline_type:
        query = query.where(Pipeline.pipeline_type == pipeline_type)
        
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()
    
    # Get items
    query = query.order_by(desc(Pipeline.created_at)).offset(offset).limit(size)
    result = await db.execute(query)
    pipelines = result.scalars().all()
    
    return PipelineListResponse(
        items=pipelines,
        total=total,
        page=page,
        size=size
    )


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pipeline details."""
    query = select(Pipeline).where(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.user_id == current_user.user_id
    )
    result = await db.execute(query)
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    return pipeline


@router.get("/{pipeline_id}/tasks", response_model=List[PipelineTaskResponse])
async def list_pipeline_tasks(
    pipeline_id: UUID,
    status: Optional[str] = None,
    failed_only: bool = False,
    page: int = Query(1, gt=0),
    size: int = Query(50, gt=0, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tasks for a pipeline."""
    # Verify pipeline ownership
    p_query = select(Pipeline).where(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.user_id == current_user.user_id
    )
    p_result = await db.execute(p_query)
    if not p_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    offset = (page - 1) * size
    
    query = select(PipelineTask).where(PipelineTask.pipeline_id == pipeline_id)
    
    if failed_only:
        query = query.where(PipelineTask.status == 'failed')
    elif status:
        query = query.where(PipelineTask.status == status)
        
    query = query.order_by(desc(PipelineTask.created_at)).offset(offset).limit(size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return tasks


@router.post("/{pipeline_id}/cancel", status_code=200)
async def cancel_pipeline_endpoint(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running pipeline."""
    # Verify ownership
    query = select(Pipeline).where(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.user_id == current_user.user_id
    )
    result = await db.execute(query)
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    if pipeline.status in ['completed', 'cancelled', 'failed']:
        return {"message": f"Pipeline is already {pipeline.status}"}
        
    await cancel_pipeline(str(pipeline_id))
    
    return {"message": "Pipeline cancellation requested"}


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a pipeline record and its tasks (does not delete photos)."""
    # Verify ownership
    query = select(Pipeline).where(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.user_id == current_user.user_id
    )
    result = await db.execute(query)
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    # Cancel if running
    if pipeline.status == 'running':
        await cancel_pipeline(str(pipeline_id))
        
    await db.delete(pipeline)
    await db.commit()
    
    return None


@router.post("/{pipeline_id}/rerun", status_code=202)
async def rerun_pipeline(
    pipeline_id: UUID,
    request: RerunPipelineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rerun failed or specific tasks in a pipeline."""
    from app.celery_app import celery_app
    
    # Verify ownership
    query = select(Pipeline).where(
        Pipeline.pipeline_id == pipeline_id,
        Pipeline.user_id == current_user.user_id
    )
    result = await db.execute(query)
    pipeline = result.scalar_one_or_none()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    if pipeline.status == 'running':
        raise HTTPException(status_code=400, detail="Pipeline is currently running")
        
    # Find tasks to rerun
    task_query = select(PipelineTask).where(PipelineTask.pipeline_id == pipeline_id)
    
    if request.task_ids:
        task_query = task_query.where(PipelineTask.task_id.in_(request.task_ids))
    elif request.failed_only:
        statuses = ['failed']
        if request.include_skipped:
            statuses.append('skipped')
        task_query = task_query.where(PipelineTask.status.in_(statuses))
    else:
        # Rerun all? Careful!
        pass
        
    result = await db.execute(task_query)
    tasks = result.scalars().all()
    
    if not tasks:
        return {"message": "No tasks found to rerun"}
        
    # Update pipeline status
    pipeline.status = 'running'
    pipeline.started_at = datetime.utcnow()
    pipeline.completed_at = None
    pipeline.error = None
    
    rerun_count = 0
    for task in tasks:
        # Reset task status
        task.status = 'queued'
        task.error_message = None
        task.error_type = None
        task.completed_at = None
        task.started_at = None
        task.retry_count = 0
        
        # Enqueue worker based on pipeline type
        # Assuming all tasks are photo processing for now
        # Ideally we'd store which step failed, but for now restart from initial if possible
        # Or if we know it failed at analysis, we could just run analysis?
        # Simpler: always run full process for now, or check if initial passed?
        
        # Check if initial processing passed (e.g. hash exists)
        # But simpler to just re-queue initial
        
        task_name = 'app.workers.thumbnail_worker.process_photo_initial'
        
        # Send task
        celery_task = celery_app.send_task(
            task_name,
            args=[str(task.photo_id), str(task.photo_id)], # upload_id=photo_id for reruns
            kwargs={'pipeline_id': str(pipeline_id)}
        )
        task.celery_task_id = celery_task.id
        rerun_count += 1
        
    await db.commit()
    
    return {
        "message": f"Rerunning {rerun_count} tasks",
        "pipeline_id": str(pipeline_id)
    }
