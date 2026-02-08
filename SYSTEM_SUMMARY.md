# RAMP — Full System Summary

**Research Accountability & Mastery Platform (Viva AI)**  
Backend: FastAPI, SQLAlchemy 2 async, PostgreSQL/SQLite.

---

## 1. Directory Tree

```
c:\Viva AI\
├── .env
├── .env.example
├── alembic.ini
├── requirements.txt
├── ramp_dev.db                 # SQLite dev DB (if used)
├── SYSTEM_SUMMARY.md           # This file
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 20260205_0001_initial_schema.py
│       └── 20260205_0002_mastery_verification.py
│
├── data/
│   └── question_bank.json      # Tier 1/2/3 questions for mastery
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Settings (DB, auth, rate limit, email)
│   ├── database.py             # Async engine, get_db, init_db
│   ├── main.py                 # FastAPI app, CORS, rate limit, routes
│   │
│   ├── ai/                     # AI Isolation Zone
│   │   ├── __init__.py
│   │   ├── prose_limits.py     # Word limits per suggestion type
│   │   ├── sandbox.py          # Suggestion types, sandbox interface
│   │   ├── suggestion_queue.py
│   │   └── watermark.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # get_db, get_current_user, RequireProjectView/Edit, get_client_ip
│   │   ├── middleware/
│   │   │   ├── capability_check.py   # AI capability gate per request
│   │   │   └── rate_limit.py         # Per-IP/auth rate limiting
│   │   └── v1/
│   │       ├── __init__.py     # Mounts all v1 routers
│   │       ├── auth.py         # Register, login, refresh, logout, me, change-password
│   │       ├── projects.py     # CRUD, share, collaborators
│   │       ├── artifacts.py    # CRUD, link, history, tree
│   │       ├── collaboration.py# Threads, comments, reviews
│   │       ├── mastery.py      # Progress, checkpoints, capabilities, AI request
│   │       ├── validation.py   # Run validation (citations)
│   │       ├── verification.py # Pending, create, respond (content verification)
│   │       └── export.py       # Integrity report, DOCX export
│   │
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── audit/
│   │   │   ├── contribution_scorer.py  # Modification ratio, category, paste detection
│   │   │   ├── effort_gate_service.py  # Claim-evidence links, notes words
│   │   │   ├── export_controller.py    # Export decision (integrity, mastery)
│   │   │   └── integrity_calculator.py # Score components, blocking issues
│   │   ├── mastery/
│   │   │   ├── ai_disclosure_controller.py # Level 0–4, capabilities, requirements
│   │   │   ├── checkpoint_service.py   # Tier 1/2/3 attempt, pass/fail
│   │   │   ├── grader.py               # Grade MC, T/F, word count
│   │   │   ├── progress_tracker.py     # get_progress, tier, ai_level
│   │   │   └── question_bank.py        # Tier 1/2/3 questions from JSON/code
│   │   └── validation/
│   │       ├── format_validator.py     # DOI, ISBN, arXiv, year
│   │       ├── existence_checker.py    # Crossref, OpenLibrary, arXiv (cached)
│   │       ├── red_flag_detector.py    # Date mismatch, author mismatch
│   │       ├── content_verifier.py
│   │       ├── cross_project_checker.py
│   │       └── validation_service.py   # Orchestrates 5-layer citation
│   │
│   ├── kernel/
│   │   ├── __init__.py
│   │   ├── events/
│   │   │   ├── event_store.py  # log(), count_events()
│   │   │   └── event_types.py  # Pydantic payloads per event
│   │   ├── identity/
│   │   │   ├── identity_service.py # register, authenticate, get_user, refresh
│   │   │   ├── jwt.py              # create/verify tokens
│   │   │   └── password.py         # hash, verify
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── user.py          # User, UserRole, RefreshToken
│   │   │   ├── project.py       # ResearchProject, ProjectShare, DisciplineType, ProjectStatus
│   │   │   ├── artifact.py      # Artifact, ArtifactVersion, ArtifactLink, Claim, Evidence, Source, etc.
│   │   │   ├── collaboration.py # CommentThread, Comment, ReviewRequest, ApprovalGate
│   │   │   ├── event_log.py     # EventLog, EventType
│   │   │   ├── permission.py    # Permission, ResourceType
│   │   │   ├── mastery.py       # UserMasteryProgress, CheckpointAttempt
│   │   │   └── verification.py  # ContentVerificationRequest
│   │   └── permissions/
│   │       └── permission_service.py  # project access, share, levels
│   │
│   ├── plugins/
│   │   ├── __init__.py
│   │   └── disciplines/
│   │       ├── base.py         # Base discipline pack
│   │       ├── stem.py
│   │       ├── humanities.py
│   │       ├── social_sciences.py
│   │       └── legal.py
│   │
│   └── schemas/
│       ├── __init__.py
│       ├── common.py           # HealthResponse, SuccessResponse, PaginatedResponse
│       ├── auth.py             # Register, Login, TokenResponse, UserResponse
│       ├── project.py          # ProjectCreate, ProjectResponse, ProjectListResponse, etc.
│       ├── artifact.py         # ArtifactCreate, ArtifactResponse, ArtifactLinkCreate, etc.
│       ├── collaboration.py   # CommentThread, Comment, ReviewRequest, etc.
│       ├── mastery.py          # MasteryProgressResponse, CheckpointStart/Result, CapabilitiesResponse
│       ├── validation.py
│       ├── verification.py
│       └── ai_suggestion.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # db_engine, db_session, test_user, test_project, auth_headers
    ├── integration/
    │   └── test_auth_api.py     # (skipped; requires DB)
    ├── system/
    │   └── test_system_smoke.py # Health, register/login, full flow, mastery progress
    └── unit/
        ├── test_contribution_scorer.py
        ├── test_existence_checker.py
        ├── test_mastery.py
        ├── test_password.py
        └── test_validation.py
```

---

## 2. API Endpoints (Full Paths)

Base: `/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| **Auth** | | |
| POST | `/auth/register` | Register user |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Refresh token |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Current user |
| PATCH | `/auth/me` | Update profile |
| POST | `/auth/change-password` | Change password |
| **Projects** | | |
| POST | `/projects` | Create project |
| GET | `/projects` | List (owned + shared) |
| GET | `/projects/{project_id}` | Get project |
| PATCH | `/projects/{project_id}` | Update project |
| DELETE | `/projects/{project_id}` | Delete project |
| POST | `/projects/{project_id}/share` | Share with user |
| GET | `/projects/{project_id}/collaborators` | List collaborators |
| DELETE | `/projects/{project_id}/collaborators/{user_id}` | Remove collaborator |
| **Mastery** | | |
| GET | `/projects/{project_id}/mastery/progress` | Progress (tier, ai_level, words) |
| POST | `/projects/{project_id}/mastery/checkpoint/{tier}/start` | Start Tier 1/2/3 |
| POST | `/projects/{project_id}/mastery/checkpoint/{tier}/submit` | Submit attempt |
| GET | `/projects/{project_id}/mastery/capabilities` | Available AI capabilities |
| POST | `/projects/{project_id}/mastery/capabilities/{capability}/request` | Request AI (e.g. outline) |
| **Validation** | | |
| POST | `/projects/{project_id}/validation/run` | Run citation validation |
| **Artifacts** | | |
| POST | `/artifacts/projects/{project_id}/artifacts` | Create artifact |
| GET | `/artifacts/{artifact_id}` | Get artifact (with links) |
| PATCH | `/artifacts/{artifact_id}` | Update artifact |
| DELETE | `/artifacts/{artifact_id}` | Soft delete |
| POST | `/artifacts/{artifact_id}/link` | Create link (target, link_type) |
| GET | `/artifacts/{artifact_id}/history` | Version history |
| GET | `/artifacts/projects/{project_id}/tree` | Artifact tree |
| **Collaboration** | | |
| POST | `/artifacts/{artifact_id}/threads` | Create comment thread |
| GET | `/artifacts/{artifact_id}/threads` | List threads |
| POST | `/threads/{thread_id}/comments` | Add comment |
| PATCH | `/threads/{thread_id}/resolve` | Resolve thread |
| POST | `/projects/{project_id}/reviews` | Request review |
| GET | `/projects/{project_id}/reviews` | List reviews |
| PATCH | `/reviews/{review_id}/respond` | Respond to review |
| **Export** | | |
| GET | `/projects/{project_id}/integrity` | Integrity report (incl. effort gates) |
| POST | `/projects/{project_id}/export/docx` | Export DOCX (blocked if gates fail) |
| **Verification** | | |
| GET | `/verification/pending` | Pending content verification requests |
| POST | `/verification/requests` | Create request |
| POST | `/verification/requests/{request_id}/respond` | Respond |

**Other**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/` | API info |

---

## 3. Kernel Models (Stable Kernel)

| Model | Table | Purpose |
|-------|--------|---------|
| **User** | users | Identity, role (student/advisor/admin), password_hash |
| **RefreshToken** | refresh_tokens | JWT refresh |
| **ResearchProject** | research_projects | Title, discipline, status, owner, integrity_score, export_blocked |
| **ProjectShare** | project_shares | Shared with, permission_level |
| **Artifact** | artifacts | type, parent_id, position, content, content_hash, version, contribution_category, ai_modification_ratio |
| **ArtifactVersion** | artifact_versions | Immutable history |
| **ArtifactLink** | artifact_links | source/target, link_type (supports, cites, contains, …) |
| **Claim** | claims | claim_type, confidence_level, requires_evidence |
| **Evidence** | evidence | evidence_type, strength_rating, source_refs |
| **Source** | sources | citation_data, doi, isbn, uri, verification_status |
| **ProvenanceRecord** | provenance_records | source_id, verification_hash, verified_by |
| **CommentThread** | comment_threads | artifact_id, resolved |
| **Comment** | comments | thread_id, author_id, body |
| **ReviewRequest** | review_requests | project_id, reviewer_id, status |
| **ApprovalGate** | approval_gates | gate_name, passed |
| **EventLog** | event_logs | event_type, entity_*, user_id, payload, ip_address |
| **Permission** | permissions | resource_type, resource_id, user_id, level |
| **UserMasteryProgress** | user_mastery_progress | user_id, project_id, current_tier, ai_disclosure_level, total_words_written, tier_*_completed_at |
| **CheckpointAttempt** | checkpoint_attempts | user_id, project_id, checkpoint_type, passed, score |
| **ContentVerificationRequest** | content_verification_requests | source/claim verification |

**Enums (examples)**  
ArtifactType (section, claim, evidence, source, note, method, result, discussion), LinkType (supports, contradicts, cites, contains, extends, qualifies), ContributionCategory (primarily_human, human_guided, ai_reviewed, unmodified_ai), VerificationStatus (unverified, format_valid, exists_verified, content_verified, flagged), ProjectStatus (draft, active, submitted, archived), DisciplineType (stem, humanities, social_sciences, legal, mixed), UserRole (student, advisor, admin), ReviewStatus (pending, in_progress, approved, changes_requested, rejected).

---

## 4. Event Types (Audit Log)

| Category | EventType | Description |
|----------|-----------|-------------|
| User | user.registered, user.logged_in, user.logged_out, user.updated, user.role_changed | |
| Project | project.created, project.updated, project.deleted, project.status_changed, project.shared, project.unshared, project.exported | |
| Artifact | artifact.created, artifact.updated, artifact.deleted, artifact.linked, artifact.unlinked, artifact.moved | |
| Collaboration | comment.added, comment.edited, comment.deleted, thread.resolved, thread.reopened, review.requested, review.responded | |
| AI | ai.suggestion_generated, ai.suggestion_accepted, ai.suggestion_rejected, ai.suggestion_modified | |
| Mastery | mastery.checkpoint_started, mastery.checkpoint_passed, mastery.checkpoint_failed, mastery.tier_upgraded, mastery.ai_level_unlocked | |
| Validation | validation.citation_verified, validation.citation_flagged, validation.red_flag_detected | |
| Export | export.requested, export.completed, export.blocked, export.integrity_report | |
| Admin | admin.advisor_override, admin.bulk_operation | |

---

## 5. AI Disclosure Levels & Capabilities

| Level | Name | Unlock | Capabilities |
|-------|------|--------|--------------|
| 0 | No AI | Default | — |
| 1 | Search Assistant | Tier 1 passed (80%) | search_queries, source_recommendations, pdf_extraction |
| 2 | Structural Assistant | Tier 2 passed (3×150 words) | + outline_suggestions, gap_analysis, claim_evidence_linking |
| 3 | Drafting Assistant | Tier 2 + 5000 words | + paragraph_suggestions, source_summaries, method_templates |
| 4 | Simulation Mode | Tier 3 passed (85%) | + defense_questions, examiner_simulation, contradiction_detection |

---

## 6. Engines & Capabilities

| Engine | Module | Responsibility |
|--------|--------|----------------|
| **Audit** | contribution_scorer | Modification ratio, ContributionCategory, PasteDetector |
| | effort_gate_service | Claim–evidence links ≥3, notes words ≥200; blocks export if failed |
| | export_controller | ExportDecision (integrity, unmodified AI, mastery, status) |
| | integrity_calculator | Score (contribution, citation, structure, mastery), blocking_issues |
| **Mastery** | ai_disclosure_controller | Level 0–4, LEVEL_CAPABILITIES, get_available_capabilities, has_capability |
| | checkpoint_service | start_checkpoint, submit_attempt (Tier 1/2/3), pass thresholds |
| | grader | Grade MC/TF, Tier 2 word count |
| | progress_tracker | get_progress (tier, ai_level, words), checkpoint_attempts |
| | question_bank | get_tier_1_questions(5), get_tier_2_prompts(3), get_tier_3_questions(10) from data/question_bank.json |
| **Validation** | format_validator | DOI, ISBN, arXiv, year |
| | existence_checker | Crossref, OpenLibrary, arXiv (cached), rate limit |
| | red_flag_detector | Date/author mismatch, red flags |
| | validation_service | Orchestrates format → existence → content → cross-project → red flags |

---

## 7. Effort Gates (Export Blocking)

- **Claim–evidence links**: ≥3 links (SUPPORTS/CITES) from CLAIM to EVIDENCE artifacts.
- **Notes words**: ≥200 words total in NOTE-type artifacts.
- Time-per-words (30 min/1000 words) not implemented (no session tracking).
- Evaluated in `EffortGateService.evaluate_project()`; failed gates appear in integrity report and block DOCX export.

---

## 8. Rate Limiting (API Gateway)

- **Auth** (POST `/api/v1/auth/*`): 10 requests/min per IP.
- **General API**: 100 requests/min per user (from JWT) or per IP if unauthenticated.
- Config: `rate_limit_auth_per_minute`, `rate_limit_api_per_minute`, `rate_limit_enabled` in config.
- Implemented in `src/api/middleware/rate_limit.py`.

---

## 9. Plugins (Discipline Packs)

- **Base** (`plugins/disciplines/base.py`): Abstract discipline pack.
- **STEM, Humanities, Social Sciences, Legal**: Each can define validation rules / thresholds (extensible).

---

## 10. Configuration (config.py)

- **Database**: database_url (PostgreSQL or SQLite+aiosqlite).
- **Security**: secret_key, algorithm, access_token_expire_minutes.
- **Email**: smtp_host, smtp_port, smtp_user, smtp_password, smtp_from_email.
- **App**: debug, environment, api_v1_prefix, project_name, version.
- **Rate limit**: rate_limit_auth_per_minute (10), rate_limit_api_per_minute (100), rate_limit_ai_per_hour (20), rate_limit_enabled.

---

## 11. Tests

| Suite | Location | Count | Notes |
|-------|----------|-------|--------|
| Unit | tests/unit/ | 53 | contribution_scorer, existence_checker, mastery, password, validation |
| Integration | tests/integration/ | 6 | test_auth_api (skipped; requires DB) |
| System | tests/system/ | 4 | Health, register/login, full flow, mastery progress (SQLite override) |

**Run all**: `pytest tests/` → 57 passed, 6 skipped.

---

## 12. Data File

- **data/question_bank.json**: tier_1 (5 questions), tier_2 (3 defend_approach prompts), tier_3 (10 short_answer questions). Loaded by `QuestionBank` for randomized mastery checkpoints.

---

This document is the single reference for the RAMP/Viva AI backend: file tree, API surface, kernel models, events, AI levels, engines, effort gates, rate limits, plugins, config, and tests.
