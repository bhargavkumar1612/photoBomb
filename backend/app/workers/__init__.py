"""Workers module initialization."""
from app.workers.thumbnail_worker import process_upload

__all__ = ["process_upload"]
