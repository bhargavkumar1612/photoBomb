from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, desc
from pydantic import BaseModel, field_validator
from typing import List, Optional
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.models.person import Person
from app.models.photo import Photo
# Replaced AdminJob with Pipeline
from app.models.pipeline import Pipeline, PipelineTask
from sqlalchemy import func
import logging

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

class ClusterRequest(BaseModel):
    target_user_ids: List[uuid.UUID]
    scopes: List[str]  # "faces", "animals", "hashtags"
    force_reset: bool = False

class AdminUserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    is_admin: bool = False

    @field_validator('is_admin', mode='before')
    @classmethod
    def set_false_if_none(cls, v):
        return v or False

# Mapped to match old AdminJobResponse for frontend compatibility
class AdminJobResponse(BaseModel):
    job_id: uuid.UUID
    job_type: str
    status: str
    scopes: List[str]
    target_user_ids: List[uuid.UUID]
    force_reset: bool
    progress_current: int
    progress_total: int
    message: Optional[str]
    error: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users for admin selection."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

@router.get("/jobs", response_model=List[AdminJobResponse])
async def list_jobs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent admin jobs with their status.
    Now queries the `pipelines` table and maps it to the expected format.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Query Pipelines that are 'admin_cluster' type (or legacy types)
    # We include 'admin_cluster' and others to be safe, or just filter by prefix 'admin_'?
    # For now, let's grab all or filter by relevant types if needed. 
    # The existing frontend expects 'cluster' jobs mainly.
    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.pipeline_type.in_(['admin_cluster', 'batch_analysis', 'rescan']))
        .order_by(desc(Pipeline.created_at))
        .limit(limit)
    )
    pipelines = result.scalars().all()
    
    # Map Pipeline -> AdminJobResponse
    response_list = []
    for p in pipelines:
        # Extract config to reconstruct AdminJob fields
        config = p.config or {}
        
        # Determine job_type for frontend (if it expects specific strings)
        job_type = p.pipeline_type
        if job_type == 'admin_cluster':
            job_type = 'cluster'
            
        created_at_str = p.created_at.isoformat() if p.created_at else None
        started_at_str = p.started_at.isoformat() if p.started_at else None
        completed_at_str = p.completed_at.isoformat() if p.completed_at else None

        response_list.append(AdminJobResponse(
            job_id=p.pipeline_id,
            job_type=job_type,
            status=p.status,
            scopes=config.get('scopes', []),
            target_user_ids=[uuid.UUID(uid) for uid in config.get('target_user_ids', [])],
            force_reset=config.get('force_reset', False),
            progress_current=p.completed_photos,
            progress_total=p.total_photos,
            message=p.description, # Map description to message
            error=p.error,
            created_at=created_at_str,
            started_at=started_at_str,
            completed_at=completed_at_str,
        ))
        
    return response_list


@router.post("/cluster")
async def trigger_admin_clustering(
    request: ClusterRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to trigger heavy maintenance tasks.
    Creates a Pipeline record and starts processing.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # config json for the pipeline
    config = {
        "scopes": request.scopes,
        "target_user_ids": [str(uid) for uid in request.target_user_ids],
        "force_reset": request.force_reset
    }

    # Create Pipeline record
    pipeline = Pipeline(
        user_id=current_user.user_id,
        pipeline_type="admin_cluster",
        name=f"Admin Cluster: {', '.join(request.scopes)}",
        description="Job started",
        status="running",
        config=config,
        started_at=func.now(),
        total_photos=0, # Will be updated by background task
        completed_photos=0,
        job_type="cluster" # Legacy field required by DB constraint
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)

    # Offload to background task
    background_tasks.add_task(
        process_clustering_job,
        pipeline.pipeline_id,
        request
    )

    return {"status": "queued", "job_id": str(pipeline.pipeline_id), "message": "Job queued in background"}


async def process_clustering_job(pipeline_id: uuid.UUID, request: ClusterRequest):
    """
    Background task to handle the actual clustering logic.
    Updates the Pipeline record.
    """
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        print(f"🔄 BackgroundTask started for pipeline {pipeline_id}, scopes={request.scopes}", flush=True)
        try:
             # Fetch pipeline to update it
            result = await session.execute(select(Pipeline).where(Pipeline.pipeline_id == pipeline_id))
            pipeline = result.scalar_one_or_none()
            if not pipeline:
                return

            results = []
            
            for user_id in request.target_user_ids:
                user_msg = []
                # Verify target user exists
                result = await session.execute(select(User).where(User.user_id == user_id))
                target_user = result.scalar_one_or_none()
                if not target_user:
                    results.append(f"User {user_id}: Not Found")
                    continue

                prefix = f"User {target_user.email}:"

                # 1. Faces
                if "faces" in request.scopes:
                    if request.force_reset:
                        # Delete all persons for user
                        await session.execute(delete(Person).where(Person.user_id == user_id))
                        await session.commit()
                        user_msg.append("Faces reset")
                    
                    from app.celery_app import celery_app
                    try:
                        # Trigger face clustering worker
                        celery_app.send_task('app.workers.face_worker.cluster_faces', args=[str(user_id)])
                        user_msg.append("Face clustering queued")
                    except Exception as e:
                        user_msg.append(f"Face clustering FAILED: {e}")

                # 2. Animals
                if "animals" in request.scopes:
                    from app.celery_app import celery_app
                    try:
                        celery_app.send_task(
                            'app.workers.face_worker.cluster_animals',
                            args=[str(user_id)],
                            kwargs={'force_reset': request.force_reset}
                        )
                        user_msg.append("Animal clustering queued")
                    except Exception as e:
                        user_msg.append(f"Animal clustering FAILED: {e}")

                # 3. Hashtags / Rescan (The main part that uses PipelineTasks)
                if "hashtags" in request.scopes:
                    # Fetch photos to process
                    query = select(Photo).where(Photo.user_id == user_id, Photo.deleted_at == None)
                    
                    if request.force_reset:
                        # Reset processed status
                        await session.execute(
                            update(Photo)
                            .where(Photo.user_id == user_id)
                            .values(processed_at=None)
                        )
                        await session.commit()
                        user_msg.append("Reset processed status")
                    else:
                        # Only retry unprocessed
                        query = query.where(Photo.processed_at == None)

                    # Execute query
                    photo_result = await session.execute(query)
                    photos = photo_result.scalars().all()
                    
                    if photos:
                        from app.celery_app import celery_app
                        # Add to total count
                        pipeline.total_photos += len(photos)
                        await session.commit()

                        count = 0
                        for photo in photos:
                            try:
                                # Create PipelineTask record
                                task = PipelineTask(
                                    pipeline_id=pipeline_id,
                                    photo_id=photo.photo_id,
                                    photo_filename=photo.filename,
                                    status='queued'
                                )
                                session.add(task)
                                # Send task with pipeline_id
                                celery_app.send_task(
                                    'app.workers.thumbnail_worker.process_photo_analysis',
                                    args=[str(photo.photo_id), str(photo.photo_id)],
                                    kwargs={'pipeline_id': str(pipeline_id)}
                                )
                                count += 1
                            except Exception as e:
                                print(f"❌ Failed to send task: {e}", flush=True)
                        
                        await session.commit()
                        user_msg.append(f"Queued {count} photos for analysis")
                    else:
                        user_msg.append("No photos to rescan")

                if user_msg:
                     results.append(f"{prefix} {', '.join(user_msg)}")
                else:
                     results.append(f"{prefix} No scopes selected")

            # Update pipeline 
            has_async_tasks = "hashtags" in request.scopes and pipeline.total_photos > 0
            
            pipeline.description = " | ".join(results)
            if not has_async_tasks:
                pipeline.status = "completed"
                pipeline.completed_at = func.now()
            
            await session.commit()
            
        except Exception as e:
            print(f"💥 Error in background clustering: {e}", flush=True)
            # Try to update job status to failed
            try:
                pipeline.status = "failed"
                pipeline.error_message = str(e)
                await session.commit()
            except:
                pass
