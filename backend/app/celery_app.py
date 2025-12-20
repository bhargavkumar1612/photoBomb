"""
Celery application configuration.
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "photobomb",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'app.workers.thumbnail_worker.*': {'queue': 'high'},
        'app.workers.face_worker.*': {'queue': 'low'},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['app.workers'])
