"""
Checkpoint Service - Evaluates tiered mastery checkpoints.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class CheckpointType(str, Enum):
    """Types of mastery checkpoints."""
    TIER_1_COMPREHENSION = "tier_1_comprehension"  # 5 questions, 80% pass
    TIER_2_ANALYSIS = "tier_2_analysis"  # 3 prompts, 150 words each
    TIER_3_DEFENSE = "tier_3_defense"  # 10 questions, 85% pass


class QuestionResult(BaseModel):
    """Result for a single question/prompt."""
    
    question_id: uuid.UUID
    correct: bool
    user_answer: str
    expected_answer: Optional[str] = None
    word_count: Optional[int] = None


class CheckpointResult(BaseModel):
    """Result of a checkpoint evaluation."""
    
    checkpoint_type: CheckpointType
    user_id: uuid.UUID
    project_id: uuid.UUID
    
    # Scores
    total_questions: int
    correct_answers: int
    score_percentage: float
    passed: bool
    
    # Details
    question_results: List[QuestionResult]
    
    # Metadata
    attempt_number: int
    time_spent_seconds: int
    completed_at: datetime
    
    # Unlocks
    tier_unlocked: Optional[int] = None
    ai_level_unlocked: Optional[int] = None


class CheckpointService:
    """
    Evaluates mastery checkpoints for tier progression.
    
    Tier 1: Section Understanding
    - 5 comprehension questions about the current section
    - 80% pass rate required (4/5 correct)
    - Unlocks: AI outline suggestions, source recommendations
    
    Tier 2: Critical Analysis
    - 3 "defend your approach" prompts
    - 150 words minimum each
    - Unlocks: AI claim refinement, argument gap analysis
    
    Tier 3: Defense Readiness
    - 10 oral-exam style questions
    - 85% pass rate required (8.5/10, rounded up to 9)
    - Unlocks: Export with integrity report
    """
    
    # Pass thresholds
    TIER_1_PASS_RATE = 0.80  # 80%
    TIER_2_MIN_WORDS = 150
    TIER_3_PASS_RATE = 0.85  # 85%
    
    # Question counts
    TIER_1_QUESTION_COUNT = 5
    TIER_2_PROMPT_COUNT = 3
    TIER_3_QUESTION_COUNT = 10
    
    @classmethod
    def evaluate_tier_1(
        cls,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        answers: List[QuestionResult],
        attempt_number: int,
        time_spent: int,
    ) -> CheckpointResult:
        """
        Evaluate Tier 1 comprehension checkpoint.
        
        Args:
            user_id: User taking the checkpoint
            project_id: Project being evaluated
            answers: List of answered questions
            attempt_number: Which attempt this is
            time_spent: Time spent in seconds
            
        Returns:
            CheckpointResult with pass/fail status
        """
        correct = sum(1 for a in answers if a.correct)
        score = correct / len(answers) if answers else 0
        passed = score >= cls.TIER_1_PASS_RATE
        
        return CheckpointResult(
            checkpoint_type=CheckpointType.TIER_1_COMPREHENSION,
            user_id=user_id,
            project_id=project_id,
            total_questions=len(answers),
            correct_answers=correct,
            score_percentage=score * 100,
            passed=passed,
            question_results=answers,
            attempt_number=attempt_number,
            time_spent_seconds=time_spent,
            completed_at=datetime.utcnow(),
            tier_unlocked=1 if passed else None,
            ai_level_unlocked=1 if passed else None,
        )
    
    @classmethod
    def evaluate_tier_2(
        cls,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        responses: List[QuestionResult],
        attempt_number: int,
        time_spent: int,
    ) -> CheckpointResult:
        """
        Evaluate Tier 2 critical analysis checkpoint.
        
        All prompts must have at least 150 words.
        """
        # Check word counts
        all_sufficient = all(
            (r.word_count or 0) >= cls.TIER_2_MIN_WORDS
            for r in responses
        )
        
        # Mark as correct if word count met
        for r in responses:
            r.correct = (r.word_count or 0) >= cls.TIER_2_MIN_WORDS
        
        correct = sum(1 for r in responses if r.correct)
        score = correct / len(responses) if responses else 0
        passed = all_sufficient and len(responses) >= cls.TIER_2_PROMPT_COUNT
        
        return CheckpointResult(
            checkpoint_type=CheckpointType.TIER_2_ANALYSIS,
            user_id=user_id,
            project_id=project_id,
            total_questions=len(responses),
            correct_answers=correct,
            score_percentage=score * 100,
            passed=passed,
            question_results=responses,
            attempt_number=attempt_number,
            time_spent_seconds=time_spent,
            completed_at=datetime.utcnow(),
            tier_unlocked=2 if passed else None,
            ai_level_unlocked=2 if passed else None,
        )
    
    @classmethod
    def evaluate_tier_3(
        cls,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        answers: List[QuestionResult],
        attempt_number: int,
        time_spent: int,
    ) -> CheckpointResult:
        """
        Evaluate Tier 3 defense readiness checkpoint.
        """
        correct = sum(1 for a in answers if a.correct)
        score = correct / len(answers) if answers else 0
        passed = score >= cls.TIER_3_PASS_RATE
        
        return CheckpointResult(
            checkpoint_type=CheckpointType.TIER_3_DEFENSE,
            user_id=user_id,
            project_id=project_id,
            total_questions=len(answers),
            correct_answers=correct,
            score_percentage=score * 100,
            passed=passed,
            question_results=answers,
            attempt_number=attempt_number,
            time_spent_seconds=time_spent,
            completed_at=datetime.utcnow(),
            tier_unlocked=3 if passed else None,
            ai_level_unlocked=4 if passed else None,
        )
    
    @classmethod
    def get_required_questions(cls, checkpoint_type: CheckpointType) -> int:
        """Get the number of questions required for a checkpoint type."""
        return {
            CheckpointType.TIER_1_COMPREHENSION: cls.TIER_1_QUESTION_COUNT,
            CheckpointType.TIER_2_ANALYSIS: cls.TIER_2_PROMPT_COUNT,
            CheckpointType.TIER_3_DEFENSE: cls.TIER_3_QUESTION_COUNT,
        }.get(checkpoint_type, 5)
    
    @classmethod
    def get_pass_threshold(cls, checkpoint_type: CheckpointType) -> float:
        """Get the pass threshold for a checkpoint type."""
        return {
            CheckpointType.TIER_1_COMPREHENSION: cls.TIER_1_PASS_RATE,
            CheckpointType.TIER_2_ANALYSIS: 1.0,  # All prompts must meet word count
            CheckpointType.TIER_3_DEFENSE: cls.TIER_3_PASS_RATE,
        }.get(checkpoint_type, 0.8)
