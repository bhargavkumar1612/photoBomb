"""
Authentication API endpoints.
Implements register, login, and JWT refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import User
from app.models.photo import Photo
from sqlalchemy import func
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()


# Pydantic schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecureP@ssw0rd123",
                "full_name": "Jane Doe"
            }
        }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


# Dependency to get current user from JWT
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract user from JWT access token."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Fetch user from database
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.
    Returns JWT tokens immediately after registration.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        full_name=request.full_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.user_id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,  # 1 hour
        user={
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "face_recognition_enabled": user.face_recognition_enabled
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email and password.
    Returns JWT access token and refresh token.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        # Delay response to prevent timing attacks
        import asyncio
        await asyncio.sleep(0.2)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        import asyncio
        await asyncio.sleep(0.2)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is deleted
    if user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deleted"
        )
    
    # Generate tokens
    access_token = create_access_token(data={
        "sub": str(user.user_id),
        "email": user.email,
        "face_enabled": user.face_recognition_enabled
    })
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user={
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "face_recognition_enabled": user.face_recognition_enabled
        }
    )


@router.post("/refresh")
async def refresh_token_endpoint(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify user exists
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Generate new access token
    access_token = create_access_token(data={
        "sub": str(user.user_id),
        "email": user.email,
        "face_enabled": user.face_recognition_enabled
    })
    
    return {
                "access_token": access_token,
                "expires_in": 3600
            }


class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login or register with Google OAuth.
    Verifies Google ID token and creates/updates user.
    """
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    
    try:
        # Verify Google ID token
        idinfo = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Extract user info from token
        google_id = idinfo['sub']
        email = idinfo['email']
        full_name = idinfo.get('name', email.split('@')[0])
        
        # Check if user exists with this Google ID
        result = await db.execute(
            select(User).where(User.google_id == google_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Check if user exists with this email
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.email_verified = True
            else:
                # Create new user
                user = User(
                    email=email,
                    google_id=google_id,
                    full_name=full_name,
                    email_verified=True,
                    password_hash=None  # No password for OAuth users
                )
                db.add(user)
        
        await db.commit()
        await db.refresh(user)
        
        # Generate JWT tokens
        access_token = create_access_token(data={
            "sub": str(user.user_id),
            "email": user.email,
            "face_enabled": user.face_recognition_enabled
        })
        refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            user={
                "user_id": str(user.user_id),
                "email": user.email,
                "full_name": user.full_name,
                "face_recognition_enabled": user.face_recognition_enabled
            }
        )
        
    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user information and sync storage usage."""
    
    # Recalculate storage usage from DB to ensure accuracy
    # This acts as a self-healing mechanism on login/refresh
    result = await db.execute(
        select(func.sum(Photo.size_bytes)).where(
            Photo.user_id == current_user.user_id,
            Photo.deleted_at == None
        )
    )
    actual_storage_bytes = result.scalar() or 0
    
    if current_user.storage_used_bytes != actual_storage_bytes:
        current_user.storage_used_bytes = actual_storage_bytes
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)

    return {
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "face_recognition_enabled": current_user.face_recognition_enabled,
        "storage_used_bytes": current_user.storage_used_bytes,
        "storage_quota_bytes": current_user.storage_quota_bytes
    }

async def get_current_user_or_token(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from either Authorization header or token query parameter.
    Used for endpoints that need to work with <img> tags (which can't send headers).
    """
    # Try to get token from query param first, then header
    jwt_token = None
    
    if token:
        jwt_token = token
    elif authorization:
        scheme, _, jwt_token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
    
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Verify token (same logic as get_current_user)
    try:
        payload = jwt.decode(
            jwt_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.deleted_at == None)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user's information."""
    # Refresh user data from DB to get latest storage info
    result = await db.execute(
        select(User).where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one()
    
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "full_name": user.full_name,
        "face_enabled": user.face_enabled,
        "storage_used_bytes": user.storage_used_bytes,
        "storage_quota_bytes": user.storage_quota_bytes,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }
