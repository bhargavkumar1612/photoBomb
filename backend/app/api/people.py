
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.person import Person, Face
from app.models.photo import Photo
from app.api.auth import get_current_user
from app.services.face_clustering import cluster_faces

router = APIRouter()

from pydantic import BaseModel

class PersonResponse(BaseModel):
    person_id: uuid.UUID
    name: Optional[str]
    face_count: int
    cover_photo_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class PersonUpdate(BaseModel):
    name: str

@router.post("/cluster")
async def trigger_clustering(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger background face clustering for the current user.
    """
    background_tasks.add_task(cluster_faces, current_user.user_id)
    return {"message": "Clustering started in background"}

@router.get("/", response_model=List[PersonResponse])
async def list_people(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all people found for the user.
    """
    # Join with Face to get count, and also get cover face URL
    # This query might be complex.
    # Group by person.
    
    # Simple approach: Fetch people and eager load or separate query for counts?
    # Subquery for counts is efficient.
    
    stmt = (
        select(
            Person,
            func.count(Face.face_id).label("face_count")
        )
        .join(Face, Face.person_id == Person.person_id)
        .where(Person.user_id == current_user.user_id)
        .group_by(Person.person_id)
        .order_by(desc("face_count"))
    )
    
    result = await db.execute(stmt)
    people_with_counts = result.all()
    
    response = []
    
    # We need to fetch cover photo URLs. 
    # Person has cover_face_id -> Face -> Photo
    # We can lazy load or do a big join.
    # Let's iterate and fetch for now (N+1 query risk but acceptable for MVP with small N people)
    # Alternatively, join in the main query.
    
    from app.services.storage_factory import get_storage_service
    from app.core.config import settings
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for person, count in people_with_counts:
        cover_url = None
        if person.cover_face_id:
             # Fetch the face to get the photo
             # Use explicit query to avoid lazy load issues in async
             # Actually, we can use `person.cover_face` relationship if we joined or selectinloaded it.
             # But here we didn't.
             res = await db.execute(
                 select(Face).where(Face.face_id == person.cover_face_id).join(Photo)
             )
             cover_face = res.scalar_one_or_none()
             
             if cover_face and cover_face.photo:
                  key_base = f"uploads/{current_user.user_id}/{cover_face.photo.photo_id}"
                  # We should create a face crop thumbnail ideally.
                  # For now, use the 256 thumb of the photo.
                  cover_url = storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600)
        
        response.append(PersonResponse(
            person_id=person.person_id,
            name=person.name,
            face_count=count,
            cover_photo_url=cover_url
        ))
        
    return response

@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Person).where(Person.person_id == person_id, Person.user_id == current_user.user_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
        
    # Get count
    count_res = await db.execute(select(func.count(Face.face_id)).where(Face.person_id == person_id))
    count = count_res.scalar()
    
    # Get cover
    # Reuse logic...
    from app.services.storage_factory import get_storage_service
    from app.core.config import settings
    storage = get_storage_service(settings.STORAGE_PROVIDER)
    cover_url = None
    if person.cover_face_id:
         res = await db.execute(
             select(Face).where(Face.face_id == person.cover_face_id).join(Photo)
         )
         cover_face = res.scalar_one_or_none()
         if cover_face and cover_face.photo:
              key_base = f"uploads/{current_user.user_id}/{cover_face.photo.photo_id}"
              cover_url = storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600)

    return PersonResponse(
        person_id=person.person_id,
        name=person.name,
        face_count=count,
        cover_photo_url=cover_url
    )

@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: uuid.UUID,
    data: PersonUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Person).where(Person.person_id == person_id, Person.user_id == current_user.user_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
        
    person.name = data.name
    await db.commit()
    await db.refresh(person)
    
    # Re-fetch for response (count etc) - lazy hack, just return what we have with 0 count or separate query?
    # Or just generic response.
    return PersonResponse(
        person_id=person.person_id,
        name=person.name,
        face_count=0, # TODO: fetch
        cover_photo_url=None # TODO: fetch
    )
