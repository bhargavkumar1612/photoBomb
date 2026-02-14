"""
Models package initialization.
Exports all database models for easy importing.
"""
from app.models.user import User
from app.models.photo import Photo, PhotoFile
from app.models.album import Album
from app.models.tag import Tag, PhotoTag
from app.models.person import Person, Face
from app.models.animal import AnimalDetection
from app.models.share_link import ShareLink
from app.models.shared_photo import SharedPhoto
from app.models.pipeline import Pipeline, PipelineTask, AdminJob  # AdminJob is alias for backward compatibility

__all__ = [
    "User",
    "Photo",
    "PhotoFile",
    "Album",
    "Tag",
    "PhotoTag",
    "Person",
    "Face",
    "AnimalDetection",
    "ShareLink",
    "SharedPhoto",
    "Pipeline",
    "PipelineTask",
    "AdminJob",  # Backward compatibility
]
