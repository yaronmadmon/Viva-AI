"""
Event sourcing infrastructure.

Provides append-only audit logging with immutable events.
"""

from src.kernel.events.event_store import EventStore
from src.kernel.events.event_types import (
    BaseEvent,
    UserEvent,
    ProjectEvent,
    ArtifactEvent,
    CollaborationEvent,
    AIEvent,
    MasteryEvent,
    ValidationEvent,
    ExportEvent,
)

__all__ = [
    "EventStore",
    "BaseEvent",
    "UserEvent",
    "ProjectEvent",
    "ArtifactEvent",
    "CollaborationEvent",
    "AIEvent",
    "MasteryEvent",
    "ValidationEvent",
    "ExportEvent",
]
