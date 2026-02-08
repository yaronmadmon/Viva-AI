"""
Progress Tracker - Tracks user mastery progression (DB-backed).
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.mastery.checkpoint_service import CheckpointResult, CheckpointType
from src.kernel.models.mastery import CheckpointAttempt as CheckpointAttemptRow
from src.kernel.models.mastery import UserMasteryProgress


class CheckpointAttempt(BaseModel):
    """Record of a checkpoint attempt (Pydantic)."""

    checkpoint_type: CheckpointType
    attempt_number: int
    score_percentage: float
    passed: bool
    completed_at: datetime


class UserProgress(BaseModel):
    """User's mastery progress for a project."""

    user_id: uuid.UUID
    project_id: uuid.UUID
    current_tier: int = 0
    ai_level: int = 0
    total_words_written: int = 0
    checkpoint_attempts: List[CheckpointAttempt] = []
    tier_1_completed_at: Optional[datetime] = None
    tier_2_completed_at: Optional[datetime] = None
    tier_3_completed_at: Optional[datetime] = None
    has_advisor_override: bool = False
    override_reason: Optional[str] = None
    override_by: Optional[uuid.UUID] = None


class ProgressTracker:
    """
    Tracks and manages user mastery progression (database-backed).
    Progression rules and AI level unlocks as in docstring below.
    """

    LEVEL_3_WORD_THRESHOLD = 5000

    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_progress(self, row: UserMasteryProgress, attempts: List[CheckpointAttemptRow]) -> UserProgress:
        """Build UserProgress Pydantic from DB row and attempt rows."""
        attempt_list = []
        for i, a in enumerate(attempts):
            attempt_list.append(
                CheckpointAttempt(
                    checkpoint_type=CheckpointType(a.checkpoint_type),
                    attempt_number=i + 1,
                    score_percentage=a.score,
                    passed=a.passed,
                    completed_at=a.created_at,
                )
            )
        return UserProgress(
            user_id=row.user_id,
            project_id=row.project_id,
            current_tier=row.current_tier,
            ai_level=row.ai_disclosure_level,
            total_words_written=row.total_words_written,
            checkpoint_attempts=attempt_list,
            tier_1_completed_at=row.tier_1_completed_at,
            tier_2_completed_at=row.tier_2_completed_at,
            tier_3_completed_at=row.tier_3_completed_at,
            has_advisor_override=row.has_advisor_override,
            override_reason=row.override_reason,
            override_by=row.override_by,
        )

    async def get_progress(self, user_id: uuid.UUID, project_id: uuid.UUID) -> UserProgress:
        """Get or create user progress for a project."""
        q = select(UserMasteryProgress).where(
            UserMasteryProgress.user_id == user_id,
            UserMasteryProgress.project_id == project_id,
        )
        result = await self.session.execute(q)
        row = result.scalar_one_or_none()
        if not row:
            row = UserMasteryProgress(
                user_id=user_id,
                project_id=project_id,
            )
            self.session.add(row)
            await self.session.flush()
            await self.session.refresh(row)

        attempts_q = (
            select(CheckpointAttemptRow)
            .where(
                CheckpointAttemptRow.user_id == user_id,
                CheckpointAttemptRow.project_id == project_id,
            )
            .order_by(CheckpointAttemptRow.created_at)
        )
        attempts_result = await self.session.execute(attempts_q)
        attempts = list(attempts_result.scalars().all())
        return self._row_to_progress(row, attempts)

    async def record_checkpoint_result(self, result: CheckpointResult) -> UserProgress:
        """Record a checkpoint result and update progress."""
        attempt_row = CheckpointAttemptRow(
            user_id=result.user_id,
            project_id=result.project_id,
            checkpoint_type=result.checkpoint_type.value,
            passed=result.passed,
            score=result.score_percentage,
        )
        self.session.add(attempt_row)
        await self.session.flush()

        q = select(UserMasteryProgress).where(
            UserMasteryProgress.user_id == result.user_id,
            UserMasteryProgress.project_id == result.project_id,
        )
        r = await self.session.execute(q)
        progress_row = r.scalar_one_or_none()
        if not progress_row:
            progress_row = UserMasteryProgress(
                user_id=result.user_id,
                project_id=result.project_id,
            )
            self.session.add(progress_row)
            await self.session.flush()
            await self.session.refresh(progress_row)

        if result.passed:
            if result.checkpoint_type == CheckpointType.TIER_1_COMPREHENSION:
                if progress_row.current_tier < 1:
                    progress_row.current_tier = 1
                    progress_row.tier_1_completed_at = result.completed_at
                    progress_row.ai_disclosure_level = max(progress_row.ai_disclosure_level, 1)
            elif result.checkpoint_type == CheckpointType.TIER_2_ANALYSIS:
                if progress_row.current_tier < 2:
                    progress_row.current_tier = 2
                    progress_row.tier_2_completed_at = result.completed_at
                    progress_row.ai_disclosure_level = max(progress_row.ai_disclosure_level, 2)
            elif result.checkpoint_type == CheckpointType.TIER_3_DEFENSE:
                if progress_row.current_tier < 3:
                    progress_row.current_tier = 3
                    progress_row.tier_3_completed_at = result.completed_at
                    progress_row.ai_disclosure_level = max(progress_row.ai_disclosure_level, 4)

        await self.session.flush()
        await self.session.refresh(progress_row)
        attempts_q = (
            select(CheckpointAttemptRow)
            .where(
                CheckpointAttemptRow.user_id == result.user_id,
                CheckpointAttemptRow.project_id == result.project_id,
            )
            .order_by(CheckpointAttemptRow.created_at)
        )
        ar = await self.session.execute(attempts_q)
        return self._row_to_progress(progress_row, list(ar.scalars().all()))

    async def update_word_count(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        words_added: int,
    ) -> UserProgress:
        """Update word count and check for Level 3 unlock."""
        progress = await self.get_progress(user_id, project_id)
        q = select(UserMasteryProgress).where(
            UserMasteryProgress.user_id == user_id,
            UserMasteryProgress.project_id == project_id,
        )
        r = await self.session.execute(q)
        row = r.scalar_one_or_none()
        if not row:
            return progress
        row.total_words_written += words_added
        if (
            row.current_tier >= 2
            and row.total_words_written >= self.LEVEL_3_WORD_THRESHOLD
            and row.ai_disclosure_level < 3
        ):
            row.ai_disclosure_level = 3
        await self.session.flush()
        await self.session.refresh(row)
        attempts_q = (
            select(CheckpointAttemptRow)
            .where(
                CheckpointAttemptRow.user_id == user_id,
                CheckpointAttemptRow.project_id == project_id,
            )
            .order_by(CheckpointAttemptRow.created_at)
        )
        ar = await self.session.execute(attempts_q)
        return self._row_to_progress(row, list(ar.scalars().all()))

    async def apply_advisor_override(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        advisor_id: uuid.UUID,
        reason: str,
        target_tier: int,
        target_ai_level: int,
    ) -> UserProgress:
        """Apply an advisor override to bypass checkpoints."""
        progress = await self.get_progress(user_id, project_id)
        q = select(UserMasteryProgress).where(
            UserMasteryProgress.user_id == user_id,
            UserMasteryProgress.project_id == project_id,
        )
        r = await self.session.execute(q)
        row = r.scalar_one_or_none()
        if not row:
            row = UserMasteryProgress(user_id=user_id, project_id=project_id)
            self.session.add(row)
            await self.session.flush()
            await self.session.refresh(row)
        row.has_advisor_override = True
        row.override_reason = reason
        row.override_by = advisor_id
        row.current_tier = max(row.current_tier, target_tier)
        row.ai_disclosure_level = max(row.ai_disclosure_level, target_ai_level)
        await self.session.flush()
        await self.session.refresh(row)
        attempts_q = (
            select(CheckpointAttemptRow)
            .where(
                CheckpointAttemptRow.user_id == user_id,
                CheckpointAttemptRow.project_id == project_id,
            )
            .order_by(CheckpointAttemptRow.created_at)
        )
        ar = await self.session.execute(attempts_q)
        return self._row_to_progress(row, list(ar.scalars().all()))

    async def get_next_checkpoint(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Optional[CheckpointType]:
        """Get the next checkpoint the user needs to complete."""
        progress = await self.get_progress(user_id, project_id)
        if progress.current_tier == 0:
            return CheckpointType.TIER_1_COMPREHENSION
        if progress.current_tier == 1:
            return CheckpointType.TIER_2_ANALYSIS
        if progress.current_tier == 2:
            return CheckpointType.TIER_3_DEFENSE
        return None

    async def get_attempt_count(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        checkpoint_type: CheckpointType,
    ) -> int:
        """Get the number of attempts for a specific checkpoint."""
        from sqlalchemy import func

        q = select(func.count()).select_from(CheckpointAttemptRow).where(
            CheckpointAttemptRow.user_id == user_id,
            CheckpointAttemptRow.project_id == project_id,
            CheckpointAttemptRow.checkpoint_type == checkpoint_type.value,
        )
        r = await self.session.execute(q)
        return r.scalar() or 0
