"""
Question Bank - Randomized questions for mastery checkpoints.
Supports topic-based selection, exclude_ids (question history), and optional JSON load.
"""

import json
import random
import uuid
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class QuestionType(str, Enum):
    """Types of checkpoint questions."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    DEFEND_APPROACH = "defend_approach"


class Question(BaseModel):
    """A checkpoint question."""
    
    id: uuid.UUID
    question_type: QuestionType
    text: str
    options: Optional[List[str]] = None  # For multiple choice
    correct_answer: Optional[str] = None  # For auto-grading
    grading_rubric: Optional[str] = None  # For manual grading
    topic: str  # e.g., "methodology", "literature_review"
    difficulty: int  # 1-5


class QuestionBank:
    """
    Question bank for mastery checkpoints.
    
    STUB: Contains sample questions. Production would have:
    - 1000+ questions per checkpoint type
    - Randomization to prevent sharing
    - Topic-based selection
    - Difficulty scaling
    """
    
    # Sample Tier 1 questions (comprehension)
    TIER_1_QUESTIONS = [
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="What is the primary purpose of a literature review?",
            options=[
                "To fill pages in your thesis",
                "To demonstrate understanding of existing research and identify gaps",
                "To cite as many sources as possible",
                "To copy other researchers' work",
            ],
            correct_answer="To demonstrate understanding of existing research and identify gaps",
            topic="literature_review",
            difficulty=1,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="What distinguishes a claim from evidence?",
            options=[
                "Claims are longer than evidence",
                "Claims are assertions that require support; evidence provides that support",
                "Evidence is always quantitative",
                "There is no difference",
            ],
            correct_answer="Claims are assertions that require support; evidence provides that support",
            topic="argumentation",
            difficulty=2,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.TRUE_FALSE,
            text="A hypothesis should be falsifiable.",
            options=["True", "False"],
            correct_answer="True",
            topic="methodology",
            difficulty=1,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="What is the role of methodology in research?",
            options=[
                "To make the paper longer",
                "To explain how the research was conducted",
                "To list all sources",
                "To summarize findings",
            ],
            correct_answer="To explain how the research was conducted",
            topic="methodology",
            difficulty=1,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.MULTIPLE_CHOICE,
            text="Why is citation important in academic writing?",
            options=[
                "To avoid plagiarism and give credit to original authors",
                "To increase word count",
                "To impress readers",
                "It's optional",
            ],
            correct_answer="To avoid plagiarism and give credit to original authors",
            topic="ethics",
            difficulty=1,
        ),
    ]
    
    # Sample Tier 2 prompts (critical analysis)
    TIER_2_PROMPTS = [
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.DEFEND_APPROACH,
            text="Defend your choice of methodology. Why is it appropriate for your research questions?",
            grading_rubric="Must explain: 1) Research question fit, 2) Alternatives considered, 3) Limitations acknowledged",
            topic="methodology",
            difficulty=3,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.DEFEND_APPROACH,
            text="How does your work build upon or challenge existing literature in your field?",
            grading_rubric="Must reference: 1) Key prior works, 2) Specific contribution, 3) How gaps are addressed",
            topic="literature_review",
            difficulty=3,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.DEFEND_APPROACH,
            text="What are the main limitations of your research, and how do you address them?",
            grading_rubric="Must identify: 1) At least 2 limitations, 2) Impact on findings, 3) Mitigation strategies",
            topic="limitations",
            difficulty=3,
        ),
    ]
    
    # Sample Tier 3 questions (defense readiness)
    TIER_3_QUESTIONS = [
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.SHORT_ANSWER,
            text="What would you do if your results contradicted your hypothesis?",
            grading_rubric="Should discuss: scientific integrity, revising hypothesis, exploring explanations",
            topic="ethics",
            difficulty=4,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.SHORT_ANSWER,
            text="How would you respond to a critic who says your sample size is too small?",
            grading_rubric="Should address: statistical power, practical constraints, generalizability limitations",
            topic="methodology",
            difficulty=4,
        ),
        Question(
            id=uuid.uuid4(),
            question_type=QuestionType.SHORT_ANSWER,
            text="What is the practical significance of your findings?",
            grading_rubric="Should explain: real-world applications, who benefits, implementation considerations",
            topic="implications",
            difficulty=4,
        ),
    ]
    
    @classmethod
    def _json_path(cls) -> Path:
        """Default path to question_bank.json (project data dir)."""
        return Path(__file__).resolve().parent.parent.parent.parent / "data" / "question_bank.json"

    @classmethod
    def _load_questions_from_json(cls, path: Optional[Path] = None) -> List[dict]:
        """Load questions from JSON file if present. Returns list of dicts."""
        path = path or cls._json_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "tier_1" in data:
                return data.get("tier_1", []) + data.get("tier_2", []) + data.get("tier_3", [])
            return []
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def _parse_question_dict(cls, d: dict) -> Optional[Question]:
        """Convert a JSON dict to Question; returns None if invalid."""
        try:
            qid = d.get("id")
            id_val = uuid.UUID(str(qid)) if isinstance(qid, str) else qid
            qt = d.get("question_type", "")
            question_type = QuestionType(qt) if isinstance(qt, str) else qt
            return Question(
                id=id_val,
                question_type=question_type,
                text=str(d.get("text", "")),
                options=d.get("options"),
                correct_answer=d.get("correct_answer"),
                grading_rubric=d.get("grading_rubric"),
                topic=str(d.get("topic", "general")),
                difficulty=int(d.get("difficulty", 1)),
            )
        except (ValueError, KeyError, TypeError):
            return None

    @classmethod
    def _get_tier_1_from_json(cls, path: Optional[Path] = None) -> List[Question]:
        """Load Tier 1 questions from JSON; returns empty list if file missing or invalid."""
        path = path or cls._json_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or "tier_1" not in data:
                return []
            questions = []
            for d in data.get("tier_1", []):
                q = cls._parse_question_dict(d)
                if q:
                    questions.append(q)
            return questions
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def get_tier_1_questions(
        cls,
        count: int = 5,
        topics: Optional[List[str]] = None,
        exclude_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Question]:
        """Get randomized Tier 1 comprehension questions, optionally filtered by topic and exclude_ids."""
        questions = cls._get_tier_1_from_json()
        if not questions:
            questions = cls.TIER_1_QUESTIONS.copy()
        else:
            questions = list(questions)
        if topics:
            questions = [q for q in questions if q.topic in topics]
        if not questions:
            questions = cls.TIER_1_QUESTIONS.copy()
        if exclude_ids:
            exclude_set = set(exclude_ids)
            questions = [q for q in questions if q.id not in exclude_set]
        if not questions:
            questions = cls.TIER_1_QUESTIONS.copy()
        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _get_tier_2_from_json(cls, path: Optional[Path] = None) -> List[Question]:
        """Load Tier 2 prompts from JSON; returns empty list if file missing or invalid."""
        path = path or cls._json_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or "tier_2" not in data:
                return []
            return [q for d in data.get("tier_2", []) if (q := cls._parse_question_dict(d))]
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def _get_tier_3_from_json(cls, path: Optional[Path] = None) -> List[Question]:
        """Load Tier 3 questions from JSON; returns empty list if file missing or invalid."""
        path = path or cls._json_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or "tier_3" not in data:
                return []
            return [q for d in data.get("tier_3", []) if (q := cls._parse_question_dict(d))]
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def get_tier_2_prompts(
        cls,
        count: int = 3,
        topics: Optional[List[str]] = None,
    ) -> List[Question]:
        """Get Tier 2 analysis prompts, optionally filtered by topic."""
        prompts = cls._get_tier_2_from_json()
        if not prompts:
            prompts = cls.TIER_2_PROMPTS.copy()
        else:
            prompts = list(prompts)
        if topics:
            prompts = [p for p in prompts if p.topic in topics]
        if not prompts:
            prompts = cls.TIER_2_PROMPTS.copy()
        random.shuffle(prompts)
        return prompts[:count]

    @classmethod
    def get_tier_3_questions(
        cls,
        count: int = 10,
        project_id: Optional[uuid.UUID] = None,
        exclude_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Question]:
        """Get Tier 3 defense questions. project_id reserved for future project-specific questions."""
        from_json = cls._get_tier_3_from_json()
        questions = (from_json * 4) if from_json else (cls.TIER_3_QUESTIONS * 4)
        if exclude_ids:
            exclude_set = set(exclude_ids)
            questions = [q for q in questions if q.id not in exclude_set]
        if not questions:
            questions = cls.TIER_3_QUESTIONS * 4
        random.shuffle(questions)
        return questions[:count]
    
    @classmethod
    def check_answer(
        cls,
        question: Question,
        user_answer: str,
    ) -> bool:
        """
        Check if answer is correct.
        
        For auto-gradable questions (MC, T/F), compares to correct_answer.
        For short answer/defend, returns True (needs manual review).
        """
        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
            return user_answer.strip().lower() == (question.correct_answer or "").strip().lower()
        
        # Short answer and defend prompts need manual grading
        # For now, auto-pass if minimum word count met
        return len(user_answer.split()) >= 20
