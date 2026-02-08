"""
Authentication schemas.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """User registration request."""
    
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """User login request."""
    
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User profile response."""
    
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    verified_at: Optional[datetime] = None
    mastery_tier: int = 0
    ai_disclosure_level: int = 0
    total_words_written: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request."""
    
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class TokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
