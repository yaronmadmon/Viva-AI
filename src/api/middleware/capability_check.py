"""
Capability enforcement - require AI capability level for gated operations.
"""

import uuid
from fastapi import Depends, HTTPException, Request, status

from src.api.deps import CurrentUser, DbSession
from src.engines.mastery.ai_disclosure_controller import (
    AICapability,
    AIDisclosureController,
)
from src.engines.mastery.progress_tracker import ProgressTracker


def require_capability(capability: AICapability):
    """
    Dependency that requires the current user to have the given AI capability
    in the project (from path project_id). Raises 403 if not allowed.
    """

    async def _check(
        request: Request,
        user: CurrentUser,
        db: DbSession,
    ) -> None:
        project_id = request.path_params.get("project_id")
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id required in path for capability check",
            )
        try:
            pid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_id",
            )
        tracker = ProgressTracker(db)
        progress = await tracker.get_progress(user.id, pid)
        allowed = AIDisclosureController.has_capability(progress.ai_level, capability)
        if not allowed:
            restrictions = AIDisclosureController.get_capability_restrictions(capability)
            min_level = restrictions.get("min_level", 0)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"AI capability '{capability.value}' requires level {min_level}. Your level: {progress.ai_level}. Complete checkpoints to unlock.",
            )
        # Optionally log to event_log (CAPABILITY_REQUESTED) - can be added via EventStore

    return Depends(_check)
