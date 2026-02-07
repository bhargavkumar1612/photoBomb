"""
Celery application configuration.
"""
from celery import Celery
from app.core.config import settings
import ssl

# Configure SSL for Redis if using rediss://
redis_backend_use_ssl = {}
if settings.REDIS_URL.startswith('rediss://'):
    redis_backend_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE  # For services like Upstash that handle certs
    }

# Create Celery app
celery_app = Celery(
    "photobomb",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    broker_use_ssl=redis_backend_use_ssl if settings.REDIS_URL.startswith('rediss://') else None,
    redis_backend_use_ssl=redis_backend_use_ssl if settings.REDIS_URL.startswith('rediss://') else None,
    broker_connection_retry_on_startup=True,
)

# Configure transport options for stability
celery_app.conf.broker_transport_options = {
    'visibility_timeout': 3600,  # 1 hour
    'socket_timeout': 60,       # 60 seconds
    'socket_connect_timeout': 60,
    'socket_keepalive': True,
    'health_check_interval': 10,
}

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
        'app.workers.db_keepalive_worker.*': {'queue': 'low'},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks
# Auto-discover tasks
# celery_app.autodiscover_tasks(['app.workers'])
celery_app.conf.imports = [
    'app.workers.thumbnail_worker',
    'app.workers.db_keepalive_worker',
    'app.workers.face_worker',
]

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'keep-db-alive-every-2-hours': {
        'task': 'app.workers.db_keepalive_worker.keep_db_alive',
        'schedule': crontab(hour='*/2'),
    },
}

