from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional, Any
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.animal import Animal, AnimalDetection
from app.models.photo import Photo
from app.api.auth import get_current_user
from app.services.animal_clustering import cluster_animals
from app.services.storage_factory import get_storage_service
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter()

class AnimalResponse(BaseModel):
    animal_id: uuid.UUID
    name: Optional[str]
    count: int
    cover_photo_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class AnimalUpdate(BaseModel):
    name: str

class PhotoResponse(BaseModel):
    photo_id: str
    filename: str
    thumb_urls: dict
    taken_at: Optional[Any] = None



@router.get("", response_model=List[AnimalResponse])
async def list_animals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all animal groups found for the user."""
    stmt = (
        select(
            Animal,
            func.count(func.distinct(AnimalDetection.photo_id)).label("photo_count")
        )
        .join(AnimalDetection, AnimalDetection.animal_id == Animal.animal_id)
        .where(Animal.user_id == current_user.user_id)
        .group_by(Animal.animal_id)
        .order_by(desc("photo_count"))
    )
    
    result = await db.execute(stmt)
    animals_with_counts = result.all()
    
    response = []
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for animal, count in animals_with_counts:
        cover_url = None
        if animal.cover_detection_id:
            # We assume the crop exists in storage
            cover_url = storage.generate_presigned_url(
                f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/animals/crops/{animal.cover_detection_id}.jpg",
                expires_in=3600
            )
            
        response.append(AnimalResponse(
            animal_id=animal.animal_id,
            name=animal.name,
            count=count,
            cover_photo_url=cover_url
        ))
        
    return response

@router.get("/{animal_id}", response_model=AnimalResponse)
async def get_animal(
    animal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Animal).where(Animal.animal_id == animal_id, Animal.user_id == current_user.user_id)
    )
    animal = result.scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
        
    count_res = await db.execute(
        select(func.count(func.distinct(AnimalDetection.photo_id))).where(AnimalDetection.animal_id == animal_id)
    )
    count = count_res.scalar()
    
    storage = get_storage_service(settings.STORAGE_PROVIDER)
    cover_url = None
    if animal.cover_detection_id:
        cover_url = storage.generate_presigned_url(
            f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/animals/crops/{animal.cover_detection_id}.jpg",
            expires_in=3600
        )

    return AnimalResponse(
        animal_id=animal.animal_id,
        name=animal.name,
        count=count,
        cover_photo_url=cover_url
    )

@router.get("/{animal_id}/photos")
async def list_animal_photos(
    animal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all photos containing the specified animal."""
    # Verify animal exists
    result = await db.execute(
        select(Animal).where(Animal.animal_id == animal_id, Animal.user_id == current_user.user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Animal not found")

    stmt = (
        select(Photo)
        .distinct()
        .join(AnimalDetection, AnimalDetection.photo_id == Photo.photo_id)
        .where(
            AnimalDetection.animal_id == animal_id,
            Photo.deleted_at == None
        )
        .order_by(desc(Photo.taken_at))
    )
    
    result = await db.execute(stmt)
    photos = result.scalars().all()
    
    response = []
    storage = get_storage_service(settings.STORAGE_PROVIDER)

    for photo in photos:
        key_base = f"{settings.STORAGE_PATH_PREFIX}/{current_user.user_id}/{photo.photo_id}"
        thumb_urls = {
            "thumb_256": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_256.jpg", expires_in=3600),
            "thumb_512": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_512.jpg", expires_in=3600),
            "thumb_1024": storage.generate_presigned_url(f"{key_base}/thumbnails/thumb_1024.jpg", expires_in=3600),
            "original": storage.generate_presigned_url(f"{key_base}/original/{photo.filename}", expires_in=3600)
        }
        
        response.append({
            "photo_id": str(photo.photo_id),
            "filename": photo.filename,
            "thumb_urls": thumb_urls,
            "taken_at": photo.taken_at
        })
        
    return response

@router.patch("/{animal_id}", response_model=AnimalResponse)
async def update_animal(
    animal_id: uuid.UUID,
    data: AnimalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Animal).where(Animal.animal_id == animal_id, Animal.user_id == current_user.user_id)
    )
    animal = result.scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
        
    animal.name = data.name
    await db.commit()
    await db.refresh(animal)
    
    return await get_animal(animal.animal_id, current_user, db)
