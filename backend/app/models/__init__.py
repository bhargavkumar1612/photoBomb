"""Models module initialization - import all models here."""
from app.models.user import User
from app.models.photo import Photo, PhotoFile
from app.models.album import Album
from app.models.share_link import ShareLink

__all__ = ["User", "Photo", "PhotoFile", "Album", "ShareLink"]
