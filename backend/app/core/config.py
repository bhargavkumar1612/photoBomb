"""
Core configuration for PhotoBomb application.
Loads settings from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # App
    APP_NAME: str = "PhotoBomb"
    APP_ENV: str = "development"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DB_SCHEMA: str = "photobomb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Storage Provider
    STORAGE_PROVIDER: str = "b2_native"  # "b2_native" or "s3"

    # Backblaze B2 (Legacy/Native)
    B2_APPLICATION_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_BUCKET_ID: str = ""

    # S3 Compatible (R2, AWS, MinIO)
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION_NAME: str = "auto"
    
    # Storage
    DEFAULT_STORAGE_QUOTA_GB: int = 100
    MAX_FILE_SIZE_MB: int = 50
    STORAGE_PATH_PREFIX: str = "uploads"  # Override via env var (e.g. "uploads/dev")
    
    # Face Recognition
    FACE_RECOGNITION_ENABLED: bool = True
    FACE_MODEL_PATH: str = "./models/arcface_r100_v1.onnx"
    
    # OAuth (optional)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""
    APPLE_CLIENT_SECRET: str = ""
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def storage_quota_bytes(self) -> int:
        """Convert storage quota to bytes."""
        return self.DEFAULT_STORAGE_QUOTA_GB * 1024 * 1024 * 1024
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()