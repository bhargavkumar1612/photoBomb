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

    results = []

    for user_id in request.target_user_ids:
        user_msg = []
        
        # Verify target user exists
        result = await db.execute(select(User).where(User.user_id == user_id))
        target_user = result.scalar_one_or_none()
        if not target_user:
            results.append(f"User {user_id}: Not Found")
            continue

        prefix = f"User {target_user.email}:"

        # 1. Faces
        if "faces" in request.scopes:
            if request.force_reset:
                # Delete all persons for user (Faces will be set to NULL via CASCADE SET NULL)
                await db.execute(delete(Person).where(Person.user_id == user_id))
                await db.commit() # Commit deletion before clustering
                user_msg.append("Faces reset")
            
            # background_tasks.add_task(cluster_faces, user_id)
            from app.workers.face_worker import task_cluster_faces
            task_cluster_faces.delay(str(user_id))
            user_msg.append("Face clustering queued")

        # 2. Animals
        if "animals" in request.scopes:
            # animal clustering service handles reset logic internally
            # background_tasks.add_task(cluster_animals, user_id, force_reset=request.force_reset)
            from app.workers.face_worker import task_cluster_animals
            task_cluster_animals.delay(str(user_id), force_reset=request.force_reset)
            user_msg.append("Animal clustering queued")

        # 3. Hashtags (Re-scan)
        if "hashtags" in request.scopes:
            if request.force_reset:
                # Mark all photos as unprocessed
                await db.execute(
                    update(Photo)
                    .where(Photo.user_id == user_id)
                    .values(processed_at=None)
                )
                await db.commit()
                
                # Helper to send tasks
                from app.celery_app import celery_app
                
                # Fetch all photos to queue
                result = await db.execute(select(Photo).where(Photo.user_id == user_id))
                photos = result.scalars().all()
                
                count = 0
                for photo in photos:
                     celery_app.send_task(
                        'app.workers.thumbnail_worker.process_photo_analysis',
                        args=[str(photo.photo_id), str(photo.photo_id)]
                    )
                     count += 1
                user_msg.append(f"Rescan triggered for {count} photos")
            else:
                # Just retry unprocessed ones
                result = await db.execute(
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
                        celery_app.send_task(
                            'app.workers.thumbnail_worker.process_photo_analysis',
                            args=[str(photo.photo_id), str(photo.photo_id)]
                        )
                        count += 1
                    user_msg.append(f"Retrying analysis for {count} unprocessed photos")
        
        if user_msg:
             results.append(f"{prefix} {', '.join(user_msg)}")
        else:
             results.append(f"{prefix} No scopes selected")

    return {"status": "success", "details": " | ".join(results)}
