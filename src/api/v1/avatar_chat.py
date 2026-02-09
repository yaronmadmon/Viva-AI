"""
Avatar Teacher Chat endpoint – conversational tutoring via the teaching avatar.

Phase 1: Hardened system prompt, gpt-4o, teaching contract, OpenAI TTS.
Phase 2: Persistent conversation history, teaching mode state machine.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, and_

from src.api.deps import CurrentUser, DbSession, RequireProjectView
from src.config import get_settings
from src.kernel.models.avatar_conversation import AvatarMessage
from src.kernel.models.mastery import UserMasteryProgress
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Maximum conversation history messages to load per turn
MAX_HISTORY_MESSAGES = 20


# ── Schemas ──────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    """User message sent to the avatar teacher."""
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    """Avatar teacher response."""
    reply: str
    model_used: str = "stub"
    requires_contract: bool = False
    teaching_mode: str = "PROBE"


class SpeakIn(BaseModel):
    """Text to convert to speech."""
    text: str = Field(..., min_length=1, max_length=4096)


class HistoryMessageOut(BaseModel):
    """Single message from conversation history."""
    role: str
    text: str
    teaching_mode: Optional[str] = None
    created_at: str


class HistoryOut(BaseModel):
    """Conversation history for a project."""
    project_id: str
    messages: List[HistoryMessageOut]
    total_count: int


# ── System prompt (hardened, trimmed – Phase 1) ──────────────────────────

SYSTEM_PROMPT = (
    "You are an expert PhD supervisor and examiner at a top-tier research university.\n\n"
    "Your goal is not to help the student finish quickly, but to ensure they learn to "
    "think, argue, and write at doctoral level.\n\n"
    "You teach primarily through questioning, intellectual pressure, and calibrated feedback. "
    "You prioritize rigor over comfort and clarity over fluency.\n\n"
    "DEFAULT BEHAVIOR:\n"
    "- Default to questioning before explaining.\n"
    "- Only explain after the student attempts an answer or explicitly asks for an explanation.\n"
    "- Teach how an examiner reads and evaluates work.\n\n"
    "ACADEMIC STANDARDS:\n"
    "- Enforce academic restraint. Prevent overclaiming, generalization, and unjustified certainty.\n"
    "- Prefer cautious language ('suggests,' 'within this context,' 'evidence indicates').\n"
    "- Distinguish clearly between acceptable, strong, risky, and indefensible work.\n\n"
    "EXAMINER BEHAVIOR:\n"
    "- Challenge claims directly but fairly.\n"
    "- Ask the kinds of questions raised in a viva or examiner report.\n"
    "- Make common doctoral mistakes explicit and name them when they occur.\n\n"
    "PEDAGOGICAL APPROACH:\n"
    "- Preserve productive struggle; do not rush to correct.\n"
    "- Provide specific, calibrated feedback instead of praise.\n"
    "- Frequently ask the student to explain their reasoning and rejected alternatives.\n\n"
    "SCOPE CONTROL:\n"
    "- If a question falls outside doctoral research, academic writing, or research methodology, "
    "politely redirect to the task at hand.\n\n"
    "CONTEXT AWARENESS:\n"
    "- The student is working on a doctoral dissertation within the Viva AI platform.\n"
    "- Reference their specific work when possible, not generic advice.\n\n"
    "You are calm, precise, demanding, and fair. "
    "You do not hallucinate facts. "
    "You do not simplify below doctoral standards."
)


# ── Teaching contract ────────────────────────────────────────────────────

TEACHING_CONTRACT = (
    "Before we continue:\n\n"
    "My role is to challenge your reasoning and help you think at doctoral level. "
    "I will often ask questions before explaining, and I may push back on your answers. "
    "This can feel uncomfortable \u2014 that is intentional and part of the learning process.\n\n"
    "If at any point you want a direct explanation, you can ask for one explicitly.\n\n"
    "Are you ready to proceed this way?"
)


# ── Teaching mode definitions (Phase 2) ──────────────────────────────────

MODE_INSTRUCTIONS = {
    "PROBE": (
        "Current mode: PROBE. Ask questions only. Do not explain. "
        "Force the student to articulate their reasoning."
    ),
    "HINT": (
        "Current mode: HINT. Give partial cues and counter-questions. "
        "Never give the full answer."
    ),
    "EXPLAIN": (
        "Current mode: EXPLAIN. The student has attempted an answer or explicitly "
        "requested explanation. Explain your expert reasoning \u2014 how you think, "
        "not just what is correct."
    ),
    "EXAMINER": (
        "Current mode: EXAMINER. The student has submitted text for review. "
        "Challenge claims directly. Identify specific weaknesses. "
        "Ask viva-style follow-up questions."
    ),
    "REFLECTION": (
        "Current mode: REFLECTION. Ask the student what they learned, "
        "what they would change, and what alternatives they rejected."
    ),
}

# Keywords that trigger explicit EXPLAIN mode
_EXPLAIN_TRIGGERS = [
    "explain", "tell me", "what is", "i don't understand",
    "just give me", "help me understand", "what does",
    "can you clarify", "i'm confused", "i'm lost",
]


# ── Teaching mode state machine ──────────────────────────────────────────

def _determine_teaching_mode(
    history: List[AvatarMessage],
    user_message: str,
) -> str:
    """
    Determine the current teaching mode based on conversation history
    and the student's message.

    Rules:
    - Explicit explain request → EXPLAIN
    - Long message (>80 words) → EXAMINER (text submission for review)
    - First exchange → PROBE
    - After one student attempt → HINT
    - After two+ attempts → EXPLAIN (they've earned it)
    """
    msg_lower = user_message.lower()

    # Explicit explain request
    if any(phrase in msg_lower for phrase in _EXPLAIN_TRIGGERS):
        return "EXPLAIN"

    # Text submission: long message likely means reviewing their writing
    if len(user_message.split()) > 80:
        return "EXAMINER"

    # Count student messages in recent history (last 6 messages)
    recent = history[-6:] if len(history) > 6 else history
    student_turns = sum(1 for m in recent if m.role == "user")

    # First turn → PROBE
    if student_turns <= 1:
        return "PROBE"

    # After one attempt → HINT
    if student_turns == 2:
        return "HINT"

    # After multiple attempts → EXPLAIN
    return "EXPLAIN"


# ── Helpers: conversation history ─────────────────────────────────────────

async def _load_history(
    db, user_id: uuid.UUID, project_id: uuid.UUID,
) -> List[AvatarMessage]:
    """Load the most recent conversation messages for this user+project."""
    q = (
        select(AvatarMessage)
        .where(
            and_(
                AvatarMessage.project_id == project_id,
                AvatarMessage.user_id == user_id,
                AvatarMessage.role.in_(["user", "assistant"]),
            )
        )
        .order_by(AvatarMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    result = await db.execute(q)
    rows = list(result.scalars().all())
    rows.reverse()  # oldest first
    return rows


async def _save_message(
    db, user_id: uuid.UUID, project_id: uuid.UUID,
    role: str, content: str, teaching_mode: Optional[str] = None,
) -> AvatarMessage:
    """Persist a single message to the conversation history."""
    msg = AvatarMessage(
        user_id=user_id,
        project_id=project_id,
        role=role,
        content=content,
        teaching_mode=teaching_mode,
        token_count=len(content.split()) * 2,  # rough estimate
    )
    db.add(msg)
    await db.flush()
    return msg


async def _get_or_create_mastery(
    db, user_id: uuid.UUID, project_id: uuid.UUID,
) -> UserMasteryProgress:
    """Get or create the mastery progress row for contract checking."""
    q = select(UserMasteryProgress).where(
        and_(
            UserMasteryProgress.user_id == user_id,
            UserMasteryProgress.project_id == project_id,
        )
    )
    result = await db.execute(q)
    row = result.scalar_one_or_none()
    if not row:
        row = UserMasteryProgress(
            user_id=user_id,
            project_id=project_id,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
    return row


# ── Helpers: OpenAI chat ──────────────────────────────────────────────────

async def _openai_chat(
    messages: List[dict],
    api_key: str,
) -> tuple[str, str]:
    """Call OpenAI with the full message array."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    model = "gpt-4o"
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=900,
        temperature=0.35,
    )
    content = (response.choices[0].message.content or "").strip()
    return content, model


def _build_messages(
    history: List[AvatarMessage],
    user_message: str,
    teaching_mode: str,
) -> List[dict]:
    """
    Build the full messages array for the OpenAI call.

    Structure:
    1. System prompt (identity)
    2. Conversation history (user + assistant turns)
    3. Mode injection (current teaching mode directive)
    4. Current user message
    """
    messages: List[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # Conversation history
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Mode injection as a separate system message
    mode_instruction = MODE_INSTRUCTIONS.get(teaching_mode, MODE_INSTRUCTIONS["PROBE"])
    messages.append({"role": "system", "content": mode_instruction})

    # Current user message
    messages.append({"role": "user", "content": user_message})

    return messages


# ── Stub responses (fallback when OpenAI unavailable) ─────────────────────

_STUB_RESPONSES = {
    "help": (
        "Let me turn that around: what specifically are you stuck on? "
        "Identifying the precise obstacle is the first step to solving it."
    ),
    "source": (
        "Before I point you to databases, tell me: what is the exact claim "
        "you need to support? Finding sources starts with knowing what "
        "you\u2019re looking for."
    ),
    "write": (
        "Writing well starts with thinking well. What is the single main "
        "argument of the paragraph you\u2019re working on right now?"
    ),
    "defense": (
        "Good. Let\u2019s practice. Summarize your entire dissertation in "
        "two sentences. I\u2019ll respond the way an examiner would."
    ),
}

_DEFAULT_STUB = (
    "Before I answer, tell me: what is your best understanding of this "
    "so far? I want to see where you are before I guide you."
)


def _stub_reply(message: str) -> str:
    """Return a stub reply based on keyword matching."""
    msg_lower = message.lower()
    for keyword, response in _STUB_RESPONSES.items():
        if keyword in msg_lower:
            return response
    return _DEFAULT_STUB


# ── Main chat endpoint ────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/avatar/chat",
    response_model=ChatMessageOut,
    status_code=status.HTTP_200_OK,
)
async def avatar_chat(
    project_id: uuid.UUID,
    body: ChatMessageIn,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """
    Send a message to the teaching avatar and get a conversational reply.

    Flow:
    1. Check teaching contract acceptance
    2. Load conversation history
    3. Determine teaching mode
    4. Build messages and call OpenAI (or fallback to stub)
    5. Persist both user message and assistant reply
    """
    # ── Step 1: Teaching contract check ──
    mastery = await _get_or_create_mastery(db, user.id, project_id)

    if not mastery.teacher_contract_accepted:
        # First message from this user in this project: show contract
        # Any response to the contract counts as acceptance
        history = await _load_history(db, user.id, project_id)
        contract_shown = any(
            m.role == "assistant" and "challenge your reasoning" in m.content
            for m in history
        )

        if not contract_shown:
            # Show the contract for the first time
            await _save_message(
                db, user.id, project_id, "user", body.message,
            )
            await _save_message(
                db, user.id, project_id, "assistant", TEACHING_CONTRACT,
                teaching_mode="PROBE",
            )
            return ChatMessageOut(
                reply=TEACHING_CONTRACT,
                model_used="system",
                requires_contract=True,
                teaching_mode="PROBE",
            )
        else:
            # Student responded to contract — accept and proceed
            mastery.teacher_contract_accepted = True
            await db.flush()

    # ── Step 2: Load conversation history ──
    history = await _load_history(db, user.id, project_id)

    # ── Step 3: Determine teaching mode ──
    teaching_mode = _determine_teaching_mode(history, body.message)

    # ── Step 4: Build messages and call LLM ──
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = key.startswith("sk-your-") or key == "sk-your-openai-api-key"

    reply: str
    model_used: str

    if key and not is_placeholder:
        try:
            messages = _build_messages(history, body.message, teaching_mode)
            reply, model_used = await _openai_chat(messages, key)
        except Exception as exc:
            logger.warning("OpenAI avatar chat failed, falling back to stub: %s", exc)
            reply = _stub_reply(body.message)
            model_used = "stub"
    else:
        reply = _stub_reply(body.message)
        model_used = "stub"

    # ── Step 5: Persist messages ──
    await _save_message(
        db, user.id, project_id, "user", body.message,
        teaching_mode=teaching_mode,
    )
    await _save_message(
        db, user.id, project_id, "assistant", reply,
        teaching_mode=teaching_mode,
    )

    return ChatMessageOut(
        reply=reply,
        model_used=model_used,
        requires_contract=False,
        teaching_mode=teaching_mode,
    )


# ── History endpoint (Phase 2) ────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/avatar/history",
    response_model=HistoryOut,
    status_code=status.HTTP_200_OK,
)
async def avatar_history(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """
    Get conversation history for the teaching avatar in this project.
    Returns the most recent messages (up to MAX_HISTORY_MESSAGES).
    """
    history = await _load_history(db, user.id, project_id)

    messages = [
        HistoryMessageOut(
            role=m.role,
            text=m.content,
            teaching_mode=m.teaching_mode,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in history
    ]

    return HistoryOut(
        project_id=str(project_id),
        messages=messages,
        total_count=len(messages),
    )


# ── TTS endpoint (Phase 1 – OpenAI TTS) ──────────────────────────────────

@router.post(
    "/projects/{project_id}/avatar/speak",
    status_code=status.HTTP_200_OK,
)
async def avatar_speak(
    project_id: uuid.UUID,
    body: SpeakIn,
    _: RequireProjectView,
    user: CurrentUser,
):
    """
    Convert text to speech using OpenAI TTS.

    Returns an audio/mpeg stream (MP3).
    Voice: 'onyx' – deep, authoritative, professorial.
    Model: 'tts-1' – fast with good quality.
    """
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = key.startswith("sk-your-") or key == "sk-your-openai-api-key"

    if not key or is_placeholder:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Text-to-speech is not available (no API key configured)",
        )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=key)
        response = await client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=body.text[:4096],
            response_format="mp3",
        )

        # Use .content (bytes) directly instead of iter_bytes() which
        # returns a sync iterator incompatible with async streaming.
        audio_bytes = response.content

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "inline",
            },
        )
    except Exception as exc:
        logger.error("OpenAI TTS failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Text-to-speech generation failed",
        )
