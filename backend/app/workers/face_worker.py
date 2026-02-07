from asgiref.sync import async_to_sync
from app.celery_app import celery_app
from app.services.face_clustering import cluster_faces
from app.services.animal_clustering import cluster_animals
import uuid
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.face_worker.cluster_faces")
def task_cluster_faces(user_id_str: str):
    """
    Celery task to run face clustering.
    Arguments:
        user_id_str: UUID string of the user
    """
    logger.info(f"Starting face clustering task for user {user_id_str}")
    user_id = uuid.UUID(user_id_str)
    async_to_sync(cluster_faces)(user_id)
    logger.info(f"Finished face clustering task for user {user_id_str}")

@celery_app.task(name="app.workers.face_worker.cluster_animals")
def task_cluster_animals(user_id_str: str, force_reset: bool = False):
    """
    Celery task to run animal clustering.
    Arguments:
        user_id_str: UUID string of the user
        force_reset: Whether to unassign existing generic animals
    """
    logger.info(f"Starting animal clustering task for user {user_id_str} (reset={force_reset})")
    user_id = uuid.UUID(user_id_str)
    async_to_sync(cluster_animals)(user_id, force_reset=force_reset)
    logger.info(f"Finished animal clustering task for user {user_id_str}")
