"""Curriculum endpoints."""

import uuid

from fastapi import APIRouter, status

from src.api.deps import CurrentUser, RequireProjectView
from src.pedagogy.curriculum_engine import CurriculumEngine, LessonsEngine

router = APIRouter()


@router.get("/projects/{project_id}/curriculum/concepts")
async def get_curriculum_concepts(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    discipline: str = "stem",
):
    """Get curriculum concepts for discipline."""
    concepts = CurriculumEngine.get_concepts(discipline)
    return {
        "project_id": str(project_id),
        "discipline": discipline,
        "concepts": [c.model_dump() for c in concepts],
    }


@router.get("/projects/{project_id}/curriculum/lessons")
async def get_lesson_structure(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    discipline: str = "stem",
):
    """Get lesson structure for discipline."""
    lessons = LessonsEngine.get_lesson_structure(discipline)
    return {
        "project_id": str(project_id),
        "discipline": discipline,
        "lessons": lessons,
    }
