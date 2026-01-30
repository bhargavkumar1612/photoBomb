"""Models module initialization - import all models here."""
from app.models.user import User
from app.models.photo import Photo, PhotoFile
from app.models.album import Album
from app.models.share_link import ShareLink
from app.models.shared_photo import SharedPhoto

from app.models.person import Person, Face
from app.models.tag import Tag, PhotoTag
from app.models.animal import Animal, AnimalDetection

__all__ = ["User", "Photo", "PhotoFile", "Album", "ShareLink", "SharedPhoto", "Person", "Face", "Tag", "PhotoTag", "Animal", "AnimalDetection"]
