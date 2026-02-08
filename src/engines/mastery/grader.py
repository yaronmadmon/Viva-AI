"""
Grader - Auto-grading and word-count validation for mastery checkpoints.
"""

import uuid
from typing import Optional

from src.engines.mastery.checkpoint_service import QuestionResult
from src.engines.mastery.question_bank import Question, QuestionType


class Grader:
    """
    Grades checkpoint answers: MC/TF auto-grade, Tier 2 word count,
    open-ended marked for manual review with optional word-count pass.
    """

    TIER_2_MIN_WORDS = 150
    SHORT_ANSWER_MIN_WORDS = 20  # Optional auto-pass threshold for open-ended

    @classmethod
    def grade(
        cls,
        question: Question,
        user_answer: str,
        word_count: Optional[int] = None,
    ) -> QuestionResult:
        """
        Grade a single question/prompt response.
        For MC/TF: compare to correct_answer. For Tier 2: use word_count >= 150.
        For short_answer/defend_approach: set correct=False and needs manual review,
        or auto-pass if word count >= SHORT_ANSWER_MIN_WORDS when word_count provided.
        """
        actual_word_count = word_count if word_count is not None else len((user_answer or "").split())
        correct = False
        expected: Optional[str] = None

        if question.question_type in (QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE):
            expected = question.correct_answer
            correct = (user_answer or "").strip().lower() == (expected or "").strip().lower()
        elif question.question_type == QuestionType.DEFEND_APPROACH:
            correct = actual_word_count >= cls.TIER_2_MIN_WORDS
            expected = None
        elif question.question_type == QuestionType.SHORT_ANSWER:
            correct = actual_word_count >= cls.SHORT_ANSWER_MIN_WORDS
            expected = question.grading_rubric
        else:
            correct = False

        return QuestionResult(
            question_id=question.id,
            correct=correct,
            user_answer=user_answer or "",
            expected_answer=expected,
            word_count=actual_word_count if question.question_type == QuestionType.DEFEND_APPROACH else None,
        )

    @classmethod
    def grade_tier_2_response(cls, question: Question, user_answer: str) -> QuestionResult:
        """Grade a Tier 2 defend prompt: require TIER_2_MIN_WORDS."""
        word_count = len((user_answer or "").split())
        correct = word_count >= cls.TIER_2_MIN_WORDS
        return QuestionResult(
            question_id=question.id,
            correct=correct,
            user_answer=user_answer or "",
            expected_answer=question.grading_rubric,
            word_count=word_count,
        )
