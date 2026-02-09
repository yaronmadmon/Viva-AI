"""Defense endpoints - practice vs final viva simulation."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, and_, func

from src.api.deps import CurrentUser, DbSession, RequireProjectView
from src.engines.mastery.progress_tracker import ProgressTracker
from src.kernel.models.artifact import Artifact, ArtifactLink
from src.kernel.models.project import ResearchProject

from src.logging_config import get_logger

logger = get_logger(__name__)
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


def _default_guidance(project_id: uuid.UUID) -> dict:
    """Fallback response when guidance logic fails."""
    return {
        "project_id": str(project_id),
        "rules": [
            {
                "id": "r1",
                "message": "Add your first artifact to start building your research.",
                "priority": 1,
                "cta": "New artifact",
                "cta_path": "artifacts/new",
            }
        ],
    }


@router.get("/projects/{project_id}/guidance/next")
async def get_guidance_next(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """What should I do next? Returns contextual rules from project/artifact/mastery state."""
    try:
        rules = []
        priority = 0

        # Artifact count for this project
        ac = await db.execute(
            select(func.count(Artifact.id)).where(
                and_(
                    Artifact.project_id == project_id,
                    Artifact.deleted_at.is_(None),
                )
            )
        )
        artifact_count = ac.scalar() or 0

        # Link count (links whose source artifact is in this project)
        if artifact_count > 0:
            subq = select(Artifact.id).where(
                and_(
                    Artifact.project_id == project_id,
                    Artifact.deleted_at.is_(None),
                )
            )
            lc = await db.execute(
                select(func.count(ArtifactLink.id)).where(
                    ArtifactLink.source_artifact_id.in_(subq)
                )
            )
            link_count = lc.scalar() or 0
        else:
            link_count = 0

        # Mastery progress (current_tier)
        tracker = ProgressTracker(db)
        progress = await tracker.get_progress(user.id, project_id)
        current_tier = progress.current_tier

        # Rule: no artifacts -> add first artifact
        if artifact_count == 0:
            priority += 1
            rules.append({
                "id": f"r{priority}",
                "message": "Add your first artifact to start building your research.",
                "priority": priority,
                "cta": "New artifact",
                "cta_path": "artifacts/new",
            })

        # Rule: has artifacts but no links -> link claims to evidence
        if artifact_count > 0 and link_count == 0:
            priority += 1
            rules.append({
                "id": f"r{priority}",
                "message": "Link claims to evidence to strengthen your argument structure.",
                "priority": priority,
                "cta": "Graph",
                "cta_path": "graph",
            })

        # Rule: pass Tier 1 to unlock more AI help (if not yet tier 1)
        if current_tier < 1:
            priority += 1
            rules.append({
                "id": f"r{priority}",
                "message": "Complete Tier 1 checkpoint to unlock more AI suggestions.",
                "priority": priority,
                "cta": "Mastery",
                "cta_path": "mastery",
            })

        # Rule: Tier 3 for full export
        if current_tier < 3:
            priority += 1
            rules.append({
                "id": f"r{priority}",
                "message": "Complete Tier 3 checkpoint for full export.",
                "priority": priority,
                "cta": "Start checkpoint",
                "cta_path": "mastery",
            })

        if not rules:
            rules.append({
                "id": "r0",
                "message": "You're in good shape. Add more content or request a review when ready.",
                "priority": 0,
                "cta": None,
                "cta_path": None,
            })

        return {
            "project_id": str(project_id),
            "rules": rules,
        }
    except Exception as e:
        logger.exception("Guidance endpoint error: %s", e)
        return _default_guidance(project_id)


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
