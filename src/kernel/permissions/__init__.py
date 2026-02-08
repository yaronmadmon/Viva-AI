"""
Permission Core - RBAC access control.
"""

from src.kernel.permissions.permission_service import (
    PermissionService,
    check_permission,
    require_permission,
)

__all__ = [
    "PermissionService",
    "check_permission",
    "require_permission",
]
