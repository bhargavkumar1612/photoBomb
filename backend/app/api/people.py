
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

from app.api.photos import PhotoResponse
from sqlalchemy import desc
from app.models.tag import PhotoTag # Ensure models are available if needed, though we use Face/Person


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



from sqlalchemy.orm import selectinload

@router.get("", response_model=List[PersonResponse])
async def list_people(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all people found for the user.
    """
    # Join with Face to get count, and also get cover face URL
    
    stmt = (
        select(
            Person,
            func.count(func.distinct(Face.photo_id)).label("face_count")
        )
        .join(Face, Face.person_id == Person.person_id)
        .options(selectinload(Person.cover_face).selectinload(Face.photo))
        .where(Person.user_id == current_user.user_id)
        .group_by(Person.person_id)
        .order_by(desc("face_count"))
    )
    
    result = await db.execute(stmt)
    people_with_counts = result.all()
    
    response = []
    
    from app.services.storage_factory import get_storage_service
    from app.core.config import settings
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for person, count in people_with_counts:
        cover_url = None
        cover_face = person.cover_face
        
        if cover_face and cover_face.photo:
            # Use the face crop
            key = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/faces/{cover_face.face_id}.jpg"
            cover_url = storage.generate_presigned_url(key, expires_in=3600)
            
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
    count_res = await db.execute(select(func.count(func.distinct(Face.photo_id))).where(Face.person_id == person_id))
    count = count_res.scalar()
    
    # Get cover
    # Reuse logic...
    from app.services.storage_factory import get_storage_service
    from app.core.config import settings
    storage = get_storage_service(settings.STORAGE_PROVIDER)
    cover_url = None
    if person.cover_face_id:
         res = await db.execute(
             select(Face)
             .options(selectinload(Face.photo))
             .where(Face.face_id == person.cover_face_id)
         )
         cover_face = res.scalar_one_or_none()
         if cover_face and cover_face.photo:
              # Use the face crop
              key = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/faces/{cover_face.face_id}.jpg"
              cover_url = storage.generate_presigned_url(key, expires_in=3600)

    return PersonResponse(
        person_id=person.person_id,
        name=person.name,
        face_count=count,
        cover_photo_url=cover_url
    )

@router.get("/{person_id}/photos", response_model=List[PhotoResponse])
async def list_person_photos(
    person_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all photos containing the specified person.
    """
    # Verify person exists and belongs to user
    result = await db.execute(
        select(Person).where(Person.person_id == person_id, Person.user_id == current_user.user_id)
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Join Face -> Photo
    stmt = (
        select(Photo)
        .distinct()
        .join(Face, Face.photo_id == Photo.photo_id)
        .where(
            Face.person_id == person_id,
            Photo.deleted_at == None
        )
        .order_by(desc(Photo.taken_at))
    )
    
    result = await db.execute(stmt)
    photos = result.scalars().all()
    
    response = []
    
    from app.services.storage_factory import get_storage_service
    from app.core.config import settings
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    # Safe float helper
    import math
    def safe_float(val):
        if val is None: return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f): return None
            return f
        except: return None

    for photo in photos:
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        
        thumb_urls = {
            "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
            "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
            "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
            "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
        }
        
        response.append(PhotoResponse(
            photo_id=str(photo.photo_id),
            filename=photo.filename,
            mime_type=photo.mime_type,
            size_bytes=photo.size_bytes,
            taken_at=photo.taken_at,
            uploaded_at=photo.uploaded_at,
            caption=photo.caption,
            favorite=photo.favorite,
            archived=photo.archived,
            gps_lat=safe_float(photo.gps_lat),
            gps_lng=safe_float(photo.gps_lng),
            location_name=photo.location_name,
            thumb_urls=thumb_urls
        ))
        
    return response

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
