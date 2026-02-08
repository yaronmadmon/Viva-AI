"""
Pydantic schemas for mastery API.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CheckpointAttemptSummary(BaseModel):
    """Summary of a checkpoint attempt."""

    checkpoint_type: str
    passed: bool
    score: float
    completed_at: datetime


class MasteryProgressResponse(BaseModel):
    """User's current mastery status for a project."""

    current_tier: int
    ai_level: int
    total_words_written: int
    next_checkpoint: Optional[str] = None
    attempts: List[CheckpointAttemptSummary] = []


class QuestionOption(BaseModel):
    """Single option for multiple choice."""

    id: str
    text: str


class CheckpointQuestionSchema(BaseModel):
    """Question as returned for checkpoint start."""

    id: uuid.UUID
    question_type: str
    text: str
    options: Optional[List[str]] = None
    topic: str
    difficulty: int
    grading_rubric: Optional[str] = None


class CheckpointStartResponse(BaseModel):
    """Questions/prompts for a checkpoint attempt."""

    tier: int
    checkpoint_type: str
    questions: List[CheckpointQuestionSchema]
    required_count: int
    pass_threshold_description: str


class AnswerSubmitItem(BaseModel):
    """Single answer submission."""

    question_id: uuid.UUID
    user_answer: str
    word_count: Optional[int] = None


class CheckpointSubmitRequest(BaseModel):
    """Body for checkpoint submit (project_id can come from path)."""

    answers: List[AnswerSubmitItem]
    time_spent_seconds: int = 0


class QuestionResultResponse(BaseModel):
    """Single question result in checkpoint result."""

    question_id: uuid.UUID
    correct: bool
    user_answer: str
    word_count: Optional[int] = None


class CheckpointResultResponse(BaseModel):
    """Result of a checkpoint attempt."""

    checkpoint_type: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    passed: bool
    question_results: List[QuestionResultResponse]
    attempt_number: int
    tier_unlocked: Optional[int] = None
    ai_level_unlocked: Optional[int] = None


class CapabilityItem(BaseModel):
    """Single capability with description."""

    capability: str
    description: Optional[str] = None


class CapabilitiesResponse(BaseModel):
    """Available capabilities and level description."""

    ai_level: int
    level_description: str
    capabilities: List[CapabilityItem]
    next_level_requirements: str


class CapabilityRequestResponse(BaseModel):
    """Response for capability request check."""

    allowed: bool
    capability: str
    reason: str
    restrictions: dict
