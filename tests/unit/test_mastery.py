"""Unit tests for mastery engine: CheckpointService, Grader, AIDisclosureController."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.engines.mastery.ai_disclosure_controller import (
    AICapability,
    AIDisclosureController,
    LEVEL_REQUIREMENTS,
)
from src.engines.mastery.checkpoint_service import (
    CheckpointService,
    CheckpointType,
    QuestionResult,
)
from src.engines.mastery.grader import Grader
from src.engines.mastery.question_bank import Question, QuestionBank, QuestionType


class TestCheckpointService:
    """Tests for CheckpointService pass/fail thresholds."""

    def test_tier_1_pass_threshold(self):
        """Tier 1: 80% (4/5) required to pass."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        # 4 correct, 1 wrong -> 80% -> pass
        answers = [
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer="a"),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer="b"),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer="c"),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer="d"),
            QuestionResult(question_id=uuid.uuid4(), correct=False, user_answer="wrong"),
        ]
        result = CheckpointService.evaluate_tier_1(user_id, project_id, answers, 1, 60)
        assert result.passed is True
        assert result.score_percentage == 80.0
        assert result.tier_unlocked == 1

    def test_tier_1_fail_below_80(self):
        """Tier 1: below 80% fails."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        answers = [
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer="a"),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer="b"),
            QuestionResult(question_id=uuid.uuid4(), correct=False, user_answer="wrong"),
            QuestionResult(question_id=uuid.uuid4(), correct=False, user_answer="wrong"),
            QuestionResult(question_id=uuid.uuid4(), correct=False, user_answer="wrong"),
        ]
        result = CheckpointService.evaluate_tier_1(user_id, project_id, answers, 1, 60)
        assert result.passed is False
        assert result.score_percentage == 40.0
        assert result.tier_unlocked is None

    def test_tier_2_word_count_pass(self):
        """Tier 2: all 3 prompts with >= 150 words pass."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        long_text = "word " * 150
        answers = [
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer=long_text, word_count=150),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer=long_text, word_count=150),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer=long_text, word_count=150),
        ]
        result = CheckpointService.evaluate_tier_2(user_id, project_id, answers, 1, 300)
        assert result.passed is True
        assert result.tier_unlocked == 2

    def test_tier_2_fail_insufficient_words(self):
        """Tier 2: one prompt under 150 words fails."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        long_text = "word " * 150
        short_text = "word " * 50
        answers = [
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer=long_text, word_count=150),
            QuestionResult(question_id=uuid.uuid4(), correct=True, user_answer=long_text, word_count=150),
            QuestionResult(question_id=uuid.uuid4(), correct=False, user_answer=short_text, word_count=50),
        ]
        result = CheckpointService.evaluate_tier_2(user_id, project_id, answers, 1, 300)
        assert result.passed is False

    def test_tier_3_pass_85(self):
        """Tier 3: 85% (9/10) passes."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        answers = [
            QuestionResult(question_id=uuid.uuid4(), correct=(i < 9), user_answer="x")
            for i in range(10)
        ]
        result = CheckpointService.evaluate_tier_3(user_id, project_id, answers, 1, 600)
        assert result.passed is True
        assert result.score_percentage == 90.0
        assert result.ai_level_unlocked == 4


class TestAIDisclosureController:
    """Tests for AI capability levels and unlocks."""

    def test_level_0_has_no_capabilities(self):
        """Level 0 has no capabilities."""
        caps = AIDisclosureController.get_available_capabilities(0)
        assert len(caps) == 0

    def test_level_1_has_search_capabilities(self):
        """Level 1 includes search_queries, source_recommendations."""
        caps = AIDisclosureController.get_available_capabilities(1)
        assert AICapability.SEARCH_QUERIES in caps
        assert AICapability.SOURCE_RECOMMENDATIONS in caps

    def test_has_capability_level_required(self):
        """has_capability respects level."""
        assert AIDisclosureController.has_capability(0, AICapability.SEARCH_QUERIES) is False
        assert AIDisclosureController.has_capability(1, AICapability.SEARCH_QUERIES) is True
        assert AIDisclosureController.has_capability(2, AICapability.OUTLINE_SUGGESTIONS) is True
        assert AIDisclosureController.has_capability(1, AICapability.OUTLINE_SUGGESTIONS) is False

    def test_get_level_description(self):
        """Level descriptions are non-empty."""
        for level in range(5):
            desc = AIDisclosureController.get_level_description(level)
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestGrader:
    """Tests for Grader (MC, TF, word count)."""

    def test_grade_multiple_choice_correct(self):
        """Multiple choice: exact match is correct."""
        q = Question(
            id=uuid.uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="What is 2+2?",
            options=["3", "4", "5"],
            correct_answer="4",
            topic="math",
            difficulty=1,
        )
        result = Grader.grade(q, "4")
        assert result.correct is True

    def test_grade_multiple_choice_incorrect(self):
        """Multiple choice: wrong answer is incorrect."""
        q = Question(
            id=uuid.uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="What is 2+2?",
            options=["3", "4", "5"],
            correct_answer="4",
            topic="math",
            difficulty=1,
        )
        result = Grader.grade(q, "3")
        assert result.correct is False

    def test_grade_tier_2_sufficient_words(self):
        """Tier 2 prompt: >= 150 words is correct."""
        q = Question(
            id=uuid.uuid4(),
            question_type=QuestionType.DEFEND_APPROACH,
            text="Defend your method.",
            grading_rubric="150 words",
            topic="methodology",
            difficulty=3,
        )
        long = "word " * 160
        result = Grader.grade_tier_2_response(q, long)
        assert result.correct is True
        assert (result.word_count or 0) >= 150

    def test_grade_tier_2_insufficient_words(self):
        """Tier 2 prompt: under 150 words is incorrect."""
        q = Question(
            id=uuid.uuid4(),
            question_type=QuestionType.DEFEND_APPROACH,
            text="Defend your method.",
            grading_rubric="150 words",
            topic="methodology",
            difficulty=3,
        )
        short = "word " * 50
        result = Grader.grade_tier_2_response(q, short)
        assert result.correct is False


class TestQuestionBank:
    """Tests for QuestionBank topic and exclude."""

    def test_get_tier_1_with_topics(self):
        """Topic filter returns only matching questions."""
        questions = QuestionBank.get_tier_1_questions(count=10, topics=["methodology"])
        assert all(q.topic == "methodology" for q in questions)

    def test_get_tier_1_exclude_ids(self):
        """Exclude_ids removes those questions from pool."""
        all_q = QuestionBank.get_tier_1_questions(count=10)
        some_ids = [all_q[0].id, all_q[1].id]
        filtered = QuestionBank.get_tier_1_questions(count=10, exclude_ids=some_ids)
        ids_in_filtered = {q.id for q in filtered}
        assert some_ids[0] not in ids_in_filtered
        assert some_ids[1] not in ids_in_filtered

    def test_get_tier_3_returns_count(self):
        """Tier 3 returns up to requested count."""
        questions = QuestionBank.get_tier_3_questions(count=5)
        assert len(questions) <= 5
