import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import select, and_
from app.models.animal import Animal, AnimalDetection
from app.models.photo import Photo
from app.core.database import AsyncSessionLocal
import uuid
import logging

logger = logging.getLogger(__name__)

async def cluster_animals(user_id: uuid.UUID, force_reset: bool = False):
    """
    Cluster animal detections for a user into Animal entities.
    Uses DBSCAN on 512-d CLIP embeddings.
    """
    async with AsyncSessionLocal() as db:
        if force_reset:
            # Unassign all animals for this user that don't have a custom name
            # This helps fix mis-clustering
            delete_stmt = select(Animal).where(Animal.user_id == user_id, Animal.name.like("Unnamed %"))
            res = await db.execute(delete_stmt)
            animals_to_delete = res.scalars().all()
            animal_ids = [a.animal_id for a in animals_to_delete]
            
            if animal_ids:
                from sqlalchemy import update
                await db.execute(
                    update(AnimalDetection)
                    .where(AnimalDetection.animal_id.in_(animal_ids))
                    .values(animal_id=None)
                )
                for a in animals_to_delete:
                    await db.delete(a)
                await db.flush()

        # Fetch all detections with embeddings (unassigned or belonging to generic Unnamed animals)
        query = select(AnimalDetection).join(Photo).where(
            Photo.user_id == user_id,
            AnimalDetection.embedding != None,
            and_(
                AnimalDetection.animal_id == None
            )
        )
        result = await db.execute(query)
        detections = result.scalars().all()
        
        if not detections:
            logger.info("No detections ready for clustering.")
            return

        # Group by label to ensure cats and dogs never mix
        from collections import defaultdict
        label_groups = defaultdict(list)
        for det in detections:
            label_groups[det.label].append(det)

        for label_name, group_dets in label_groups.items():
            if len(group_dets) < 2:
                continue

            embeddings = [np.array(det.embedding) for det in group_dets]
            
            logger.info(f"Clustering {len(embeddings)} '{label_name}' detections...")
            
            # Use 0.52 as a middle ground for individual animal recognition
            clt = DBSCAN(eps=0.52, min_samples=2, metric="euclidean")
            clt.fit(embeddings)

            unique_labels = np.unique(clt.labels_)
            
            for label in unique_labels:
                if label == -1:
                    continue
                
                indices = np.where(clt.labels_ == label)[0]
                cluster_dets = [group_dets[i] for i in indices]
                
                new_animal = Animal(
                    user_id=user_id,
                    name=f"Unnamed {label_name.capitalize()} ({uuid.uuid4().hex[:4]})"
                )
                db.add(new_animal)
                await db.flush()
                
                for det in cluster_dets:
                    det.animal_id = new_animal.animal_id
                
                new_animal.cover_detection_id = cluster_dets[0].detection_id

        await db.commit()
        logger.info("Animal clustering complete.")
