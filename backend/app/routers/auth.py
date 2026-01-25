"""
Authentication routes for JWT-based authentication.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    UserLogin,
    UserCreate,
    Token,
    TokenData
)
from ..auth.jwt_handler import JWT_REFRESH_TOKEN_EXPIRE_DAYS
from .. import database as db
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        user_credentials: Username and password
    
    Returns:
        Access and refresh tokens
    """
    # Get user from database
    user = db.get_user_by_username(user_credentials.username)
    
    if not user:
        logger.warning(f"Login attempt with invalid username: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(user_credentials.password, user["password_hash"]):
        logger.warning(f"Login attempt with invalid password for user: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.get("is_active", True):
        logger.warning(f"Login attempt for inactive user: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    # Create tokens
    token_data = {
        "sub": user["username"],
        "username": user["username"],
        "user_id": user["id"],
        "is_admin": user["is_admin"]
    }
    
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    
    # Save refresh token in database
    expires_at = (datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()
    db.save_session(user["id"], refresh_token, expires_at)
    
    logger.info(f"User {user_credentials.username} logged in successfully")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
    
    Returns:
        New access and refresh tokens
    """
    refresh_token = request.refresh_token
    # Verify refresh token
    token_data = verify_token(refresh_token, token_type="refresh")
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if session exists in database
    session = db.get_session_by_token(refresh_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if session is expired
    if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
        db.delete_session(refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user to ensure still exists and active
    user = db.get_user_by_id(token_data.user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens
    new_token_data = {
        "sub": user["username"],
        "username": user["username"],
        "user_id": user["id"],
        "is_admin": user["is_admin"]
    }
    
    new_access_token = create_access_token(data=new_token_data)
    new_refresh_token = create_refresh_token(data=new_token_data)
    
    # Delete old session and save new one
    db.delete_session(refresh_token)
    expires_at = (datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()
    db.save_session(user["id"], new_refresh_token, expires_at)
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


class LogoutRequest(BaseModel):
    """Request model for logout."""
    refresh_token: str = Field(..., description="Refresh token to invalidate")


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Logout user by invalidating refresh token.
    
    Args:
        request: Logout request with refresh token
        current_user: Current authenticated user (from access token)
    """
    # Delete session
    deleted = db.delete_session(request.refresh_token)
    
    if deleted:
        logger.info(f"User {current_user.username} logged out successfully")
        return {"message": "Logged out successfully"}
    else:
        logger.warning(f"Logout attempt with invalid refresh token for user: {current_user.username}")
        # Don't raise error, just return success (token might already be deleted)
        return {"message": "Logged out successfully"}


@router.post("/register")
async def register(user_data: UserCreate, current_user: TokenData = Depends(get_current_user)):
    """
    Register a new user (admin only).
    
    Args:
        user_data: User creation data
        current_user: Current authenticated user (must be admin)
    """
    from ..auth.dependencies import require_admin
    
    # Require admin privileges
    await require_admin(current_user)
    
    # Check if username already exists
    existing_user = db.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    # Create user
    user_id = db.create_user(
        username=user_data.username,
        password_hash=password_hash,
        email=user_data.email,
        is_admin=user_data.is_admin
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    logger.info(f"Admin {current_user.username} created new user: {user_data.username}")
    
    return {
        "message": "User created successfully",
        "user_id": user_id,
        "username": user_data.username
    }


@router.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User information
    """
    user = db.get_user_by_id(current_user.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_admin": user["is_admin"],
        "is_active": user["is_active"],
        "created_at": user["created_at"]
    }

