"""
Pydantic models for authentication.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class UserLogin(BaseModel):
    """Model for user login request."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=100, description="Password")


class UserCreate(BaseModel):
    """Model for user creation."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    email: Optional[EmailStr] = Field(None, description="Email address (optional)")
    is_admin: bool = Field(default=False, description="Admin privileges")


class Token(BaseModel):
    """Model for token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    """Model for token payload data."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    is_admin: bool = False





