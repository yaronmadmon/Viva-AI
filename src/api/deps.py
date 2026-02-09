"""
FastAPI dependencies for authentication, authorization, and database sessions.
"""

import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.kernel.models.user import User
from src.kernel.models.permission import PermissionLevel
from src.kernel.identity.jwt import verify_access_token, AccessTokenPayload
from src.kernel.identity.identity_service import IdentityService
from src.kernel.permissions.permission_service import PermissionService


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    """Dependency that yields database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: DbSession,
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    payload = verify_access_token(credentials.credentials)
    if not payload:
        return None
    
    identity_service = IdentityService(db)
    user = await identity_service.get_user_by_id(uuid.UUID(payload.sub))
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: DbSession,
) -> User:
    """Get current authenticated user or raise 401."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    identity_service = IdentityService(db)
    user = await identity_service.get_user_by_id(uuid.UUID(payload.sub))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user_optional)]


def get_request_id(request: Request) -> Optional[str]:
    """Get request correlation ID (set by RequestIdMiddleware)."""
    return getattr(request.state, "request_id", None)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


class PermissionChecker:
    """
    Dependency class for checking permissions on resources.
    
    Usage:
        @router.get("/projects/{project_id}")
        async def get_project(
            project_id: uuid.UUID,
            _: Annotated[bool, Depends(PermissionChecker("project", PermissionLevel.VIEW))],
            user: CurrentUser,
            db: DbSession,
        ):
            ...
    """
    
    def __init__(self, resource_type: str, required_level: PermissionLevel):
        self.resource_type = resource_type
        self.required_level = required_level
    
    async def __call__(
        self,
        request: Request,
        user: CurrentUser,
        db: DbSession,
    ) -> bool:
        # Extract resource ID from path parameters
        project_id = request.path_params.get("project_id")
        artifact_id = request.path_params.get("artifact_id")
        
        permission_service = PermissionService(db)
        
        if self.resource_type == "project" and project_id:
            has_permission = await permission_service.check_project_permission(
                user, uuid.UUID(project_id), self.required_level
            )
        elif self.resource_type == "artifact" and artifact_id:
            has_permission = await permission_service.check_artifact_permission(
                user, uuid.UUID(artifact_id), self.required_level
            )
        else:
            has_permission = False
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {self.required_level.value}",
            )
        
        return True


# Convenience permission dependencies
RequireProjectView = Annotated[bool, Depends(PermissionChecker("project", PermissionLevel.VIEW))]
RequireProjectComment = Annotated[bool, Depends(PermissionChecker("project", PermissionLevel.COMMENT))]
RequireProjectEdit = Annotated[bool, Depends(PermissionChecker("project", PermissionLevel.EDIT))]
RequireArtifactView = Annotated[bool, Depends(PermissionChecker("artifact", PermissionLevel.VIEW))]
RequireArtifactEdit = Annotated[bool, Depends(PermissionChecker("artifact", PermissionLevel.EDIT))]


async def require_admin(user: CurrentUser) -> User:
    """Require the current user to be an admin."""
    from src.kernel.models.user import UserRole
    
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]
