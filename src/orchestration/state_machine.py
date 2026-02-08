"""
State machine for SubmissionUnit and Artifact lifecycle.

Artifact/SubmissionUnit states are authoritative for review, defense, export.
Valid transitions and who may trigger them are defined here.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.kernel.models.artifact import Artifact, ArtifactState
from src.kernel.models.submission_unit import SubmissionUnit, SubmissionUnitState
from src.kernel.models.user import UserRole
from src.kernel.events.event_store import EventStore
from src.kernel.models.event_log import EventType


# Valid transitions: (from_state, to_state) -> roles that may trigger
_TRANSITIONS: Dict[Tuple[str, str], Set[UserRole]] = {
    # Student transitions
    (SubmissionUnitState.DRAFT.value, SubmissionUnitState.READY_FOR_REVIEW.value): {UserRole.STUDENT},
    (SubmissionUnitState.REVISIONS_REQUIRED.value, SubmissionUnitState.READY_FOR_REVIEW.value): {UserRole.STUDENT},
    (ArtifactState.DRAFT.value, ArtifactState.READY_FOR_REVIEW.value): {UserRole.STUDENT},
    (ArtifactState.REVISIONS_REQUIRED.value, ArtifactState.READY_FOR_REVIEW.value): {UserRole.STUDENT},
    # Advisor transitions
    (SubmissionUnitState.READY_FOR_REVIEW.value, SubmissionUnitState.UNDER_REVIEW.value): {UserRole.ADVISOR},
    (SubmissionUnitState.UNDER_REVIEW.value, SubmissionUnitState.APPROVED.value): {UserRole.ADVISOR},
    (SubmissionUnitState.UNDER_REVIEW.value, SubmissionUnitState.REVISIONS_REQUIRED.value): {UserRole.ADVISOR},
    (SubmissionUnitState.APPROVED.value, SubmissionUnitState.LOCKED.value): {UserRole.ADVISOR},
    (ArtifactState.READY_FOR_REVIEW.value, ArtifactState.UNDER_REVIEW.value): {UserRole.ADVISOR},
    (ArtifactState.UNDER_REVIEW.value, ArtifactState.APPROVED.value): {UserRole.ADVISOR},
    (ArtifactState.UNDER_REVIEW.value, ArtifactState.REVISIONS_REQUIRED.value): {UserRole.ADVISOR},
    (ArtifactState.APPROVED.value, ArtifactState.LOCKED.value): {UserRole.ADVISOR},
    # System transitions (advisor or system)
    (SubmissionUnitState.APPROVED.value, SubmissionUnitState.ARCHIVED.value): {UserRole.ADVISOR, UserRole.ADMIN},
    (SubmissionUnitState.LOCKED.value, SubmissionUnitState.ARCHIVED.value): {UserRole.ADVISOR, UserRole.ADMIN},
    (ArtifactState.APPROVED.value, ArtifactState.ARCHIVED.value): {UserRole.ADVISOR, UserRole.ADMIN},
    (ArtifactState.LOCKED.value, ArtifactState.ARCHIVED.value): {UserRole.ADVISOR, UserRole.ADMIN},
}


def valid_transitions(from_state: str, entity_type: str = "submission_unit") -> List[str]:
    """Return list of valid target states from given state."""
    transitions = []
    for (f, t), _ in _TRANSITIONS.items():
        if f == from_state:
            transitions.append(t)
    return list(set(transitions))


def can_transition(
    actor_role: UserRole,
    from_state: str,
    to_state: str,
    entity_type: str = "submission_unit",
) -> bool:
    """Check if actor with given role may transition from_state -> to_state."""
    key = (from_state, to_state)
    allowed = _TRANSITIONS.get(key, set())
    if UserRole.ADMIN in allowed or actor_role == UserRole.ADMIN:
        return True
    return actor_role in allowed


class StateMachine:
    """Service for performing state transitions with audit logging."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_store = EventStore(session)

    async def transition_unit(
        self,
        unit: SubmissionUnit,
        to_state: str,
        user_id: uuid.UUID,
        user_role: UserRole,
        ip_address: Optional[str] = None,
    ) -> SubmissionUnit:
        """Transition a SubmissionUnit to new state. Logs event and updates unit."""
        from_state = unit.state.value if hasattr(unit.state, "value") else str(unit.state)
        if not can_transition(user_role, from_state, to_state, "submission_unit"):
            raise ValueError(
                f"Invalid transition: {from_state} -> {to_state} for role {user_role.value}"
            )
        if to_state not in valid_transitions(from_state):
            raise ValueError(
                f"Invalid transition: {from_state} -> {to_state}"
            )

        unit.state = SubmissionUnitState(to_state)
        unit.state_changed_at = datetime.now(timezone.utc)
        unit.state_changed_by = user_id
        if to_state == SubmissionUnitState.APPROVED.value:
            unit.last_approved_at = unit.state_changed_at
            unit.approval_version = (unit.approval_version or 0) + 1

        await self.event_store.log(
            event_type=EventType.SUBMISSION_UNIT_STATE_CHANGED,
            entity_type="submission_unit",
            entity_id=unit.id,
            user_id=user_id,
            payload={
                "from_state": from_state,
                "to_state": to_state,
                "project_id": str(unit.project_id),
            },
            ip_address=ip_address,
        )
        return unit

    async def transition_artifact(
        self,
        artifact: Artifact,
        to_state: str,
        user_id: uuid.UUID,
        user_role: UserRole,
        ip_address: Optional[str] = None,
    ) -> Artifact:
        """Transition an Artifact (not in a unit) to new state."""
        from_state = artifact.internal_state.value if hasattr(artifact.internal_state, "value") else str(artifact.internal_state)
        if not can_transition(user_role, from_state, to_state, "artifact"):
            raise ValueError(
                f"Invalid transition: {from_state} -> {to_state} for role {user_role.value}"
            )

        artifact.internal_state = ArtifactState(to_state)

        await self.event_store.log(
            event_type=EventType.ARTIFACT_STATE_CHANGED,
            entity_type="artifact",
            entity_id=artifact.id,
            user_id=user_id,
            payload={
                "from_state": from_state,
                "to_state": to_state,
                "project_id": str(artifact.project_id),
            },
            ip_address=ip_address,
        )
        return artifact
