"""
JWT token management for authentication.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import get_settings


class AccessTokenPayload(BaseModel):
    """JWT access token payload."""
    
    sub: str  # User ID
    email: str
    role: str
    exp: datetime
    iat: datetime
    jti: str  # Token ID for revocation tracking
    
    class Config:
        from_attributes = True


class RefreshTokenPayload(BaseModel):
    """JWT refresh token payload."""
    
    sub: str  # User ID
    exp: datetime
    iat: datetime
    jti: str
    type: str = "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


class JWTManager:
    """
    JWT token creation and verification.
    
    Handles access tokens (short-lived) and refresh tokens (long-lived).
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        settings = get_settings()
        self.secret_key = secret_key or settings.secret_key
        self.algorithm = algorithm or settings.algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
    def create_access_token(
        self,
        user_id: uuid.UUID,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> tuple[str, datetime, str]:
        """
        Create a new access token.
        
        Args:
            user_id: User's unique identifier
            email: User's email
            role: User's role
            expires_delta: Optional custom expiration time
            
        Returns:
            Tuple of (token, expiration_datetime, token_id)
        """
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": "access",
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expire, jti
    
    def create_refresh_token(
        self,
        user_id: uuid.UUID,
        expires_delta: Optional[timedelta] = None,
    ) -> tuple[str, datetime, str]:
        """
        Create a new refresh token.
        
        Args:
            user_id: User's unique identifier
            expires_delta: Optional custom expiration time
            
        Returns:
            Tuple of (token, expiration_datetime, token_id)
        """
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(days=self.refresh_token_expire_days))
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": "refresh",
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expire, jti
    
    def create_token_pair(
        self,
        user_id: uuid.UUID,
        email: str,
        role: str,
    ) -> tuple[TokenPair, str, str]:
        """
        Create both access and refresh tokens.
        
        Args:
            user_id: User's unique identifier
            email: User's email
            role: User's role
            
        Returns:
            Tuple of (TokenPair, access_token_id, refresh_token_id)
        """
        access_token, access_exp, access_jti = self.create_access_token(
            user_id, email, role
        )
        refresh_token, refresh_exp, refresh_jti = self.create_refresh_token(user_id)
        
        expires_in = int((access_exp - datetime.now(timezone.utc)).total_seconds())
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        ), access_jti, refresh_jti
    
    def verify_access_token(self, token: str) -> Optional[AccessTokenPayload]:
        """
        Verify and decode an access token.
        
        Args:
            token: JWT access token
            
        Returns:
            AccessTokenPayload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            
            # Verify it's an access token
            if payload.get("type") != "access":
                return None
            
            return AccessTokenPayload(
                sub=payload["sub"],
                email=payload["email"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=payload["jti"],
            )
        except JWTError:
            return None
    
    def verify_refresh_token(self, token: str) -> Optional[RefreshTokenPayload]:
        """
        Verify and decode a refresh token.
        
        Args:
            token: JWT refresh token
            
        Returns:
            RefreshTokenPayload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            
            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                return None
            
            return RefreshTokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=payload["jti"],
            )
        except JWTError:
            return None
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        Create a hash of a token for storage.
        
        Used for storing refresh tokens in the database.
        
        Args:
            token: The token to hash
            
        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()


# Default manager instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get or create the default JWT manager."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


# Convenience functions
def create_access_token(
    user_id: uuid.UUID,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime, str]:
    """Create an access token."""
    return get_jwt_manager().create_access_token(user_id, email, role, expires_delta)


def create_refresh_token(
    user_id: uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime, str]:
    """Create a refresh token."""
    return get_jwt_manager().create_refresh_token(user_id, expires_delta)


def verify_access_token(token: str) -> Optional[AccessTokenPayload]:
    """Verify an access token."""
    return get_jwt_manager().verify_access_token(token)
