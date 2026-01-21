"""
FastAPI dependencies for authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from .jwt_handler import verify_token
from .models import TokenData
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for token extraction
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials from request header
    
    Returns:
        TokenData with user information
    
    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    token = credentials.credentials
    token_data = verify_token(token, token_type="access")
    
    if token_data is None:
        logger.warning("Invalid or expired access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


async def require_auth(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Dependency to require authentication (any authenticated user).
    
    Args:
        current_user: Current authenticated user from get_current_user
    
    Returns:
        TokenData with user information
    """
    return current_user


async def require_admin(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Dependency to require admin privileges.
    
    Args:
        current_user: Current authenticated user from get_current_user
    
    Returns:
        TokenData with user information
    
    Raises:
        HTTPException: 403 if user is not admin
    """
    if not current_user.is_admin:
        logger.warning(f"User {current_user.username} attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return current_user





