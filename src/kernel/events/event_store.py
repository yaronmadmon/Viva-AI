"""
Event Store service for append-only audit logging.

All state mutations MUST be logged here BEFORE commit.
This is a core architectural invariant of the system.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.kernel.models.event_log import EventLog, EventType


class EventStore:
    """
    Service for managing the immutable event log.
    
    Usage:
        event_store = EventStore(session)
        await event_store.log(
            event_type=EventType.ARTIFACT_CREATED,
            entity_type="artifact",
            entity_id=artifact.id,
            user_id=current_user.id,
            payload={"title": artifact.title, "content_hash": artifact.content_hash}
        )
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log(
        self,
        event_type: EventType,
        entity_type: str,
        entity_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> EventLog:
        """
        Log an event to the immutable audit log.
        
        This MUST be called before committing any state change.
        
        Args:
            event_type: The type of event
            entity_type: The type of entity (user, project, artifact, etc.)
            entity_id: The ID of the entity
            user_id: The ID of the user who triggered the event (optional for system events)
            payload: Additional event data
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            The created EventLog record
        """
        # Ensure payload is JSON-serializable
        if payload:
            payload = self._serialize_payload(payload)
        
        event = EventLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            payload=payload or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.session.add(event)
        # Note: Caller should flush/commit after all operations
        return event
    
    async def log_from_model(
        self,
        event_type: EventType,
        entity_type: str,
        entity_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        payload_model: BaseModel,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> EventLog:
        """
        Log an event using a Pydantic model as payload.
        
        Args:
            event_type: The type of event
            entity_type: The type of entity
            entity_id: The ID of the entity
            user_id: The ID of the user
            payload_model: A Pydantic model with the event data
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            The created EventLog record
        """
        payload = payload_model.model_dump(mode="json")
        return await self.log(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        event_types: Optional[List[EventType]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EventLog]:
        """
        Get the event history for a specific entity.
        
        Args:
            entity_type: The type of entity
            entity_id: The ID of the entity
            event_types: Optional filter for specific event types
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of EventLog records, newest first
        """
        query = select(EventLog).where(
            and_(
                EventLog.entity_type == entity_type,
                EventLog.entity_id == entity_id,
            )
        )
        
        if event_types:
            query = query.where(EventLog.event_type.in_(event_types))
        
        query = query.order_by(desc(EventLog.created_at)).offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_user_activity(
        self,
        user_id: uuid.UUID,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        event_types: Optional[List[EventType]] = None,
        limit: int = 100,
    ) -> List[EventLog]:
        """
        Get all events triggered by a specific user.
        
        Args:
            user_id: The user ID
            since: Start datetime filter
            until: End datetime filter
            event_types: Optional filter for specific event types
            limit: Maximum number of events
            
        Returns:
            List of EventLog records, newest first
        """
        query = select(EventLog).where(EventLog.user_id == user_id)
        
        if since:
            query = query.where(EventLog.created_at >= since)
        if until:
            query = query.where(EventLog.created_at <= until)
        if event_types:
            query = query.where(EventLog.event_type.in_(event_types))
        
        query = query.order_by(desc(EventLog.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_project_activity(
        self,
        project_id: uuid.UUID,
        include_artifacts: bool = True,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[EventLog]:
        """
        Get all events related to a project and optionally its artifacts.
        
        Args:
            project_id: The project ID
            include_artifacts: Whether to include artifact events
            since: Start datetime filter
            limit: Maximum number of events
            
        Returns:
            List of EventLog records, newest first
        """
        conditions = [
            and_(
                EventLog.entity_type == "project",
                EventLog.entity_id == project_id,
            )
        ]
        
        if include_artifacts:
            # Include events where project_id is in the payload
            conditions.append(
                EventLog.payload["project_id"].astext == str(project_id)
            )
        
        from sqlalchemy import or_
        query = select(EventLog).where(or_(*conditions))
        
        if since:
            query = query.where(EventLog.created_at >= since)
        
        query = query.order_by(desc(EventLog.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        event_type: Optional[EventType] = None,
        user_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Count events matching the given criteria.
        
        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            event_type: Filter by event type
            user_id: Filter by user ID
            since: Start datetime filter
            
        Returns:
            Count of matching events
        """
        from sqlalchemy import func
        
        query = select(func.count(EventLog.id))
        
        if entity_type:
            query = query.where(EventLog.entity_type == entity_type)
        if entity_id:
            query = query.where(EventLog.entity_id == entity_id)
        if event_type:
            query = query.where(EventLog.event_type == event_type)
        if user_id:
            query = query.where(EventLog.user_id == user_id)
        if since:
            query = query.where(EventLog.created_at >= since)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    def _serialize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert payload values to JSON-serializable types."""
        result = {}
        for key, value in payload.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_payload(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_payload(v) if isinstance(v, dict)
                    else str(v) if isinstance(v, uuid.UUID)
                    else v.isoformat() if isinstance(v, datetime)
                    else v
                    for v in value
                ]
            else:
                result[key] = value
        return result


# Convenience functions for common logging patterns

async def log_artifact_created(
    session: AsyncSession,
    artifact_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    artifact_type: str,
    content_hash: str,
    title: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> EventLog:
    """Log an artifact creation event."""
    store = EventStore(session)
    return await store.log(
        event_type=EventType.ARTIFACT_CREATED,
        entity_type="artifact",
        entity_id=artifact_id,
        user_id=user_id,
        payload={
            "project_id": project_id,
            "artifact_type": artifact_type,
            "content_hash": content_hash,
            "title": title,
        },
        ip_address=ip_address,
    )


async def log_artifact_updated(
    session: AsyncSession,
    artifact_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    previous_hash: str,
    new_hash: str,
    version: int,
    ip_address: Optional[str] = None,
) -> EventLog:
    """Log an artifact update event."""
    store = EventStore(session)
    return await store.log(
        event_type=EventType.ARTIFACT_UPDATED,
        entity_type="artifact",
        entity_id=artifact_id,
        user_id=user_id,
        payload={
            "project_id": project_id,
            "previous_content_hash": previous_hash,
            "new_content_hash": new_hash,
            "version_number": version,
        },
        ip_address=ip_address,
    )


async def log_ai_suggestion(
    session: AsyncSession,
    suggestion_id: uuid.UUID,
    artifact_id: uuid.UUID,
    user_id: uuid.UUID,
    suggestion_type: str,
    action: str,  # generated, accepted, rejected, modified
    modification_ratio: Optional[float] = None,
    ip_address: Optional[str] = None,
) -> EventLog:
    """Log an AI suggestion event."""
    store = EventStore(session)
    
    event_type_map = {
        "generated": EventType.AI_SUGGESTION_GENERATED,
        "accepted": EventType.AI_SUGGESTION_ACCEPTED,
        "rejected": EventType.AI_SUGGESTION_REJECTED,
        "modified": EventType.AI_SUGGESTION_MODIFIED,
    }
    
    payload = {
        "suggestion_type": suggestion_type,
        "artifact_id": artifact_id,
    }
    if modification_ratio is not None:
        payload["modification_ratio"] = modification_ratio
    
    return await store.log(
        event_type=event_type_map.get(action, EventType.AI_SUGGESTION_GENERATED),
        entity_type="ai_suggestion",
        entity_id=suggestion_id,
        user_id=user_id,
        payload=payload,
        ip_address=ip_address,
    )
