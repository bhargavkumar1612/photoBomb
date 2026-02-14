"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import auth, upload, photos, albums
from app.routers import sharing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("DEBUG: Starting init_db()...")
    await init_db()
    print("DEBUG: init_db() complete.")
    yield
    # Shutdown
    print("DEBUG: Shutting down db...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Privacy-first photo service - Google Photos alternative",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    return response

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(photos.router, prefix="/api/v1/photos", tags=["photos"])
app.include_router(albums.router, prefix="/api/v1/albums", tags=["albums"])
app.include_router(sharing.router, prefix="/api/v1", tags=["sharing"])
from app.api import people, tags, animals, hashtags as hashtags_api, admin
app.include_router(people.router, prefix="/api/v1/people", tags=["people"])
app.include_router(animals.router, prefix="/api/v1/animals", tags=["animals"])
app.include_router(hashtags_api.router, prefix="/api/v1/hashtags", tags=["hashtags"])
app.include_router(tags.router, prefix="/api/v1/tags", tags=["tags"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

from app.api import pipelines
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1/config/features")
async def get_features():
    """Get feature flags configuration."""
    return {
        "animal_detection_enabled": settings.ANIMAL_DETECTION_ENABLED,
        "face_recognition_enabled": settings.FACE_RECOGNITION_ENABLED
    }


@app.get("/healthz")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}
