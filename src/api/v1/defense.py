"""Defense endpoints - practice vs final viva simulation."""

import uuid

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, RequireProjectView
from src.kernel.models.project import ResearchProject
from sqlalchemy import select, and_

router = APIRouter()


@router.get("/projects/{project_id}/defense/practice/questions")
async def get_practice_questions(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
):
    """Get practice defense questions (unlimited, AI-scored)."""
    return {
        "project_id": str(project_id),
        "mode": "practice",
        "questions": [
            {"id": "q1", "text": "How does your hypothesis relate to your evidence?", "tier": 2},
            {"id": "q2", "text": "What are the limitations of your methods?", "tier": 3},
        ],
    }


@router.get("/projects/{project_id}/guidance/next")
async def get_guidance_next(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
):
    """What should I do next? Returns matching rules sorted by priority."""
    return {
        "project_id": str(project_id),
        "rules": [
            {"id": "r1", "message": "Complete Tier 3 checkpoint for full export", "priority": 1, "cta": "Start checkpoint"},
        ],
    }


@router.get("/projects/{project_id}/certification")
async def get_certification_status(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
):
    """Get certification package status."""
    return {
        "project_id": str(project_id),
        "ready": False,
        "components": {"mastery": False, "integrity": False, "defense": False},
    }
