"""
Permission service for RBAC access control.
"""

import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, List, Optional, Set

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.kernel.models.permission import Permission, PermissionLevel, ResourceType
from src.kernel.models.project import ProjectShare, ResearchProject, PermissionLevel as SharePermissionLevel
from src.kernel.models.user import User, UserRole


# Permission hierarchy - higher levels include all lower levels
PERMISSION_HIERARCHY = {
    PermissionLevel.NONE: 0,
    PermissionLevel.VIEW: 1,
    PermissionLevel.COMMENT: 2,
    PermissionLevel.EDIT: 3,
    PermissionLevel.ADMIN: 4,
    PermissionLevel.OWNER: 5,
}

# Map share permission levels to general permission levels
SHARE_TO_PERMISSION = {
    SharePermissionLevel.VIEW: PermissionLevel.VIEW,
    SharePermissionLevel.COMMENT: PermissionLevel.COMMENT,
    SharePermissionLevel.EDIT: PermissionLevel.EDIT,
}


class PermissionService:
    """
    Service for checking and managing permissions.
    
    Implements RBAC with support for:
    - Role-based permissions (admin, advisor, student)
    - Resource-based permissions (project shares)
    - Fine-grained permissions (explicit permission grants)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def check_project_permission(
        self,
        user: User,
        project_id: uuid.UUID,
        required_level: PermissionLevel,
    ) -> bool:
        """
        Check if user has required permission on a project.
        
        Permission sources (in order of precedence):
        1. Admin role - full access to all projects
        2. Project owner - owner level access
        3. Project share - shared permission level
        4. Explicit permission grant
        
        Args:
            user: The user to check
            project_id: The project ID
            required_level: Minimum required permission level
            
        Returns:
            True if user has sufficient permission
        """
        required_rank = PERMISSION_HIERARCHY[required_level]
        
        # Admins have full access
        if user.role == UserRole.ADMIN:
            return True
        
        # Check if user is owner
        query = select(ResearchProject).where(
            and_(
                ResearchProject.id == project_id,
                ResearchProject.owner_id == user.id,
                ResearchProject.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        if result.scalar_one_or_none():
            return True  # Owner has all permissions
        
        # Check project shares
        query = select(ProjectShare).where(
            and_(
                ProjectShare.project_id == project_id,
                ProjectShare.user_id == user.id,
            )
        )
        result = await self.session.execute(query)
        share = result.scalar_one_or_none()
        
        if share:
            share_level = SHARE_TO_PERMISSION.get(share.permission_level, PermissionLevel.VIEW)
            if PERMISSION_HIERARCHY[share_level] >= required_rank:
                return True
        
        # Check explicit permissions
        query = select(Permission).where(
            and_(
                Permission.user_id == user.id,
                Permission.resource_type == ResourceType.PROJECT,
                Permission.resource_id == project_id,
                Permission.revoked == False,
                or_(
                    Permission.expires_at.is_(None),
                    Permission.expires_at > datetime.now(timezone.utc),
                ),
            )
        )
        result = await self.session.execute(query)
        permission = result.scalar_one_or_none()
        
        if permission and PERMISSION_HIERARCHY[permission.level] >= required_rank:
            return True
        
        return False
    
    async def check_artifact_permission(
        self,
        user: User,
        artifact_id: uuid.UUID,
        required_level: PermissionLevel,
    ) -> bool:
        """
        Check if user has required permission on an artifact.
        
        Artifacts inherit permissions from their project.
        
        Args:
            user: The user to check
            artifact_id: The artifact ID
            required_level: Minimum required permission level
            
        Returns:
            True if user has sufficient permission
        """
        from src.kernel.models.artifact import Artifact
        
        # Get the artifact's project
        query = select(Artifact).where(Artifact.id == artifact_id)
        result = await self.session.execute(query)
        artifact = result.scalar_one_or_none()
        
        if not artifact:
            return False
        
        # Check project permission
        return await self.check_project_permission(user, artifact.project_id, required_level)
    
    async def get_user_projects(
        self,
        user: User,
        include_shared: bool = True,
    ) -> List[uuid.UUID]:
        """
        Get all project IDs the user has access to.
        
        Args:
            user: The user
            include_shared: Whether to include shared projects
            
        Returns:
            List of project IDs
        """
        project_ids: Set[uuid.UUID] = set()
        
        # Owned projects
        query = select(ResearchProject.id).where(
            and_(
                ResearchProject.owner_id == user.id,
                ResearchProject.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        project_ids.update(row[0] for row in result.all())
        
        if include_shared:
            # Shared projects
            query = select(ProjectShare.project_id).where(
                ProjectShare.user_id == user.id
            )
            result = await self.session.execute(query)
            project_ids.update(row[0] for row in result.all())
        
        # Admin sees all projects
        if user.role == UserRole.ADMIN:
            query = select(ResearchProject.id).where(
                ResearchProject.deleted_at.is_(None)
            )
            result = await self.session.execute(query)
            project_ids.update(row[0] for row in result.all())
        
        return list(project_ids)
    
    async def grant_permission(
        self,
        user_id: uuid.UUID,
        resource_type: ResourceType,
        resource_id: uuid.UUID,
        level: PermissionLevel,
        granted_by: uuid.UUID,
        expires_at: Optional[datetime] = None,
    ) -> Permission:
        """
        Grant an explicit permission to a user.
        
        Args:
            user_id: User to grant permission to
            resource_type: Type of resource
            resource_id: Resource ID
            level: Permission level to grant
            granted_by: User granting the permission
            expires_at: Optional expiration time
            
        Returns:
            The created Permission record
        """
        # Revoke any existing permission for this resource
        await self.revoke_permission(user_id, resource_type, resource_id)
        
        permission = Permission(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            level=level,
            granted_by=granted_by,
            expires_at=expires_at,
        )
        
        self.session.add(permission)
        return permission
    
    async def revoke_permission(
        self,
        user_id: uuid.UUID,
        resource_type: ResourceType,
        resource_id: uuid.UUID,
    ) -> bool:
        """
        Revoke a user's permission on a resource.
        
        Args:
            user_id: User whose permission to revoke
            resource_type: Type of resource
            resource_id: Resource ID
            
        Returns:
            True if a permission was revoked
        """
        query = select(Permission).where(
            and_(
                Permission.user_id == user_id,
                Permission.resource_type == resource_type,
                Permission.resource_id == resource_id,
                Permission.revoked == False,
            )
        )
        result = await self.session.execute(query)
        permission = result.scalar_one_or_none()
        
        if permission:
            permission.revoked = True
            permission.revoked_at = datetime.now(timezone.utc)
            return True
        
        return False
    
    async def get_project_collaborators(
        self,
        project_id: uuid.UUID,
    ) -> List[dict]:
        """
        Get all collaborators on a project with their permission levels.
        
        Args:
            project_id: The project ID
            
        Returns:
            List of dicts with user info and permission level
        """
        collaborators = []
        
        # Get owner
        query = select(ResearchProject, User).join(
            User, ResearchProject.owner_id == User.id
        ).where(ResearchProject.id == project_id)
        result = await self.session.execute(query)
        row = result.one_or_none()
        
        if row:
            project, owner = row
            collaborators.append({
                "user_id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
                "role": owner.role.value,
                "permission_level": "owner",
                "is_owner": True,
            })
        
        # Get shares
        query = select(ProjectShare, User).join(
            User, ProjectShare.user_id == User.id
        ).where(ProjectShare.project_id == project_id)
        result = await self.session.execute(query)
        
        for share, user in result.all():
            collaborators.append({
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "permission_level": share.permission_level.value,
                "is_owner": False,
                "accepted": share.accepted_at is not None,
            })
        
        return collaborators


# Convenience functions and decorators

async def check_permission(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    required_level: PermissionLevel,
) -> bool:
    """Check if user has permission on a project."""
    service = PermissionService(session)
    return await service.check_project_permission(user, project_id, required_level)


def require_permission(required_level: PermissionLevel):
    """
    Decorator for requiring a permission level.
    
    Usage:
        @require_permission(PermissionLevel.EDIT)
        async def update_project(project_id: uuid.UUID, current_user: User, db: AsyncSession):
            ...
    
    Note: This is a marker decorator. Actual permission checking
    should be done in the route handler or dependency.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # The actual permission check should be done
            # by a FastAPI dependency that has access to
            # the session, user, and resource ID
            return await func(*args, **kwargs)
        
        # Store the required level as metadata
        wrapper._required_permission = required_level
        return wrapper
    
    return decorator
