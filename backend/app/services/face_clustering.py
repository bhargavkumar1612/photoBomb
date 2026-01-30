from sqlalchemy import select, and_
from app.models.person import Face, Person
from app.models.photo import Photo
from app.core.database import AsyncSessionLocal
import uuid

async def cluster_faces(user_id: uuid.UUID):
    """
    Cluster unassigned faces for a user into persons using DBSCAN.
    """
    import numpy as np
    from sklearn.cluster import DBSCAN
    async with AsyncSessionLocal() as db:
        # Fetch all faces for user that are NOT assigned to a person yet
        # We need to join with Photo to filter by user_id
        query = select(Face).join(Photo).where(
            Photo.user_id == user_id,
            Face.person_id == None,
            Face.encoding != None
        )
        result = await db.execute(query)
        unassigned_faces = result.scalars().all()
        
        if not unassigned_faces:
            print("No unassigned faces found.")
            return

        encodings = [np.array(face.encoding) for face in unassigned_faces]
        
        if not encodings:
            return

        print(f"Clustering {len(encodings)} faces...")
        
        # DBSCAN parameters: 
        # eps: max distance between two samples for one to be considered as in the neighborhood of the other.
        #      0.6 is a common threshold for dlib face encodings. Lower = stricter.
        # min_samples: The number of samples (or total weight) in a neighborhood for a point to be considered as a core point.
        clt = DBSCAN(eps=0.5, min_samples=3, metric="euclidean")
        clt.fit(encodings)

        # Labels will be e.g., [0, 1, 0, -1, 1] where -1 is noise (unknown/outlier)
        unique_labels = np.unique(clt.labels_)
        
        print(f"Found {len(unique_labels) - (1 if -1 in unique_labels else 0)} clusters.")

        for label in unique_labels:
            if label == -1:
                # Noise/Outliers - we leave them unassigned or maybe mark them as 'unknown' if we had such state?
                # For now, leave as None. They might be clustered later when more photos are added.
                continue
            
            # Find all faces in this cluster
            indices = np.where(clt.labels_ == label)[0]
            cluster_faces = [unassigned_faces[i] for i in indices]
            
            # Create a NEW Person for this cluster
            # TODO: Improve this to check against EXISTING persons (merge/assign)
            # For now, we assume simple clustering of purely unassigned faces creates new people.
            # Real-world logic needs to finding nearest neighbors among existing persons too.
            
            # Check if we should merge with existing person? 
            # Simple approach: Calculate centroid of this new cluster and compare with existing people's centroids?
            # For Phase 2 MVP, let's just create new people for valid clusters.
            
            new_person = Person(
                user_id=user_id,
                name=f"Person {uuid.uuid4().hex[:8]}" # Placeholder name
            )
            db.add(new_person)
            await db.flush() # Get ID
            
            for face in cluster_faces:
                face.person_id = new_person.person_id
            
            # Set cover face (first one or best one?)
            if cluster_faces:
                new_person.cover_face_id = cluster_faces[0].face_id

        await db.commit()
        print("Clustering complete.")
