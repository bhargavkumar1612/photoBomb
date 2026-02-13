from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from pydantic import BaseModel, field_validator
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.services.face_clustering import cluster_faces
from app.services.animal_clustering import cluster_animals
from app.models.person import Person
from app.models.animal import Animal
from app.models.photo import Photo
from app.models.admin_job import AdminJob
from sqlalchemy import func

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
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


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
    """Get recent admin jobs with their status."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    result = await db.execute(
        select(AdminJob)
        .order_by(AdminJob.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()
    
    return [
        AdminJobResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            scopes=job.scopes,
            target_user_ids=[uuid.UUID(uid) for uid in job.target_user_ids],
            force_reset=job.force_reset,
            progress_current=job.progress_current,
            progress_total=job.progress_total,
            message=job.message,
            error=job.error,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )
        for job in jobs
    ]


@router.post("/cluster")
async def trigger_admin_clustering(
    request: ClusterRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to trigger heavy maintenance tasks.
    Supports running on multiple users.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Create job record
    job = AdminJob(
        user_id=current_user.user_id,
        job_type="cluster",
        status="running",
        target_user_ids=[str(uid) for uid in request.target_user_ids],
        scopes=request.scopes,
        force_reset=request.force_reset,
        message="Job started",
        started_at=func.now()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # TEST: Verify celery broker connection BEFORE background task
    from app.celery_app import celery_app
    try:
        # Send a test ping to the broker
        celery_app.broker_connection().ensure_connection(max_retries=3)
        print(f"✅ Celery broker connection SUCCESS before BackgroundTask", flush=True)
    except Exception as e:
        print(f"❌ Celery broker connection FAILED: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Celery broker unreachable: {e}")

    # Offload to background task
    background_tasks.add_task(
        process_clustering_job,
        job.job_id,
        request
    )


    return {"status": "queued", "job_id": str(job.job_id), "message": "Job queued in background"}


@router.post("/test-cluster-direct")
async def test_cluster_direct(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test endpoint: calls process_clustering_job directly without BackgroundTasks"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    print(f"🧪 TEST: Calling process_clustering_job directly...", flush=True)
    test_request = ClusterRequest(
        target_user_ids=[current_user.user_id],
        scopes=["faces"],
        force_reset=False
    )
    
    # Create a dummy job
    job = AdminJob(
        user_id=current_user.user_id,
        job_type="test",
        status="running",
        target_user_ids=[str(current_user.user_id)],
        scopes=["faces"],
        force_reset=False,
        message="Test job",
        started_at=func.now()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Call directly
    await process_clustering_job(job.job_id, test_request)
    
    return {"status": "test completed", "job_id": str(job.job_id)}


async def process_clustering_job(job_id: uuid.UUID, request: ClusterRequest):
    """
    Background task to handle the actual clustering logic.
    Note: We need a new session or careful management if db is passed.
    Actually, FastAPI dependency injection for 'db' closes the session after request.
    So we might need to handle session within this function if we can't reuse the request one safely.
    For simplicity in this refactor, we'll try to use the passed session but ideally we should create a new one.
    However, since we are in async context, let's keep it simple first. 
    Actually, safe way is to pass the logic to a service function that manages its own transaction or assumes one.
    But to avoid 'Session is closed' errors, we should be careful.
    
    Correction: The 'db' session from Depends(get_db) is closed after the response is sent.
    We CANNOT use it in background_tasks.
    We need to create a new session generator here.
    """
    # Re-import to avoid circular dependency if needed, or use the global SessionLocal like get_db does
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        print(f"🔄 BackgroundTask started for job {job_id}, scopes={request.scopes}", flush=True)
        try:
             # Fetch job again to update it
            result = await session.execute(select(AdminJob).where(AdminJob.job_id == job_id))
            job = result.scalar_one_or_none()
            if not job:
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
                        # Delete all persons for user (Faces will be set to NULL via CASCADE SET NULL)
                        await session.execute(delete(Person).where(Person.user_id == user_id))
                        await session.commit()
                        user_msg.append("Faces reset")
                    
                    from app.celery_app import celery_app
                    try:
                        celery_app.send_task('app.workers.face_worker.cluster_faces', args=[str(user_id)])
                        print(f"✅ Face clustering task sent for user {user_id}", flush=True)
                        user_msg.append("Face clustering queued")
                    except Exception as e:
                        print(f"❌ Failed to send face clustering task: {e}", flush=True)
                        user_msg.append(f"Face clustering FAILED: {e}")

                # 2. Animals
                if "animals" in request.scopes:
                    # animal clustering service handles reset logic internally
                    from app.celery_app import celery_app
                    try:
                        celery_app.send_task(
                            'app.workers.face_worker.cluster_animals',
                            args=[str(user_id)],
                            kwargs={'force_reset': request.force_reset}
                        )
                        print(f"✅ Animal clustering task sent for user {user_id}", flush=True)
                        user_msg.append("Animal clustering queued")
                    except Exception as e:
                        print(f"❌ Failed to send animal clustering task: {e}", flush=True)
                        user_msg.append(f"Animal clustering FAILED: {e}")

                # 3. Hashtags (Re-scan)
                if "hashtags" in request.scopes:
                    if request.force_reset:
                        # Mark all photos as unprocessed
                        await session.execute(
                            update(Photo)
                            .where(Photo.user_id == user_id)
                            .values(processed_at=None)
                        )
                        await session.commit()
                        
                        from app.celery_app import celery_app
                        # Fetch all photos to queue
                        result = await session.execute(select(Photo).where(Photo.user_id == user_id))
                        photos = result.scalars().all()
                        
                        count = 0
                        for photo in photos:
                            try:
                                celery_app.send_task(
                                    'app.workers.thumbnail_worker.process_photo_analysis',
                                    args=[str(photo.photo_id), str(photo.photo_id)]
                                )
                                count += 1
                            except Exception as e:
                                print(f"❌ Failed to send hashtag task: {e}", flush=True)
                                break
                        user_msg.append(f"Rescan triggered for {count} photos")
                    else:
                        # Retry unprocessed
                        result = await session.execute(
                            select(Photo).where(
                                Photo.user_id == user_id,
                                Photo.deleted_at == None,
                                Photo.processed_at == None
                            )
                        )
                        photos = result.scalars().all()
                        if photos:
                            from app.celery_app import celery_app
                            count = 0
                            for photo in photos:
                                try:
                                    celery_app.send_task(
                                        'app.workers.thumbnail_worker.process_photo_analysis',
                                        args=[str(photo.photo_id), str(photo.photo_id)]
                                    )
                                    count += 1
                                except Exception as e:
                                    print(f"❌ Failed to send retry hashtag task: {e}", flush=True)
                                    break
                            user_msg.append(f"Retrying analysis for {count} unprocessed photos")
                
                if user_msg:
                     results.append(f"{prefix} {', '.join(user_msg)}")
                else:
                     results.append(f"{prefix} No scopes selected")

            # Update job as completed
            job.status = "completed"
            job.completed_at = func.now()
            job.message = " | ".join(results)
            await session.commit()
            
        except Exception as e:
            print(f"💥 Error in background clustering: {e}", flush=True)
            # Try to update job status to failed
            try:
                job.status = "failed"
                job.error = str(e)
                await session.commit()
            except:
                pass
