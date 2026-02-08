"""
API v1 routes.
"""

from fastapi import APIRouter

from src.api.v1 import auth, projects, artifacts, collaboration, export, mastery, verification, validation, submission_units, examiner, curriculum, defense

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(submission_units.router, tags=["Submission Units"])
router.include_router(examiner.router, tags=["Examiner"])
router.include_router(curriculum.router, tags=["Curriculum"])
router.include_router(defense.router, tags=["Defense"])
router.include_router(mastery.router, prefix="/projects/{project_id}/mastery", tags=["Mastery"])
router.include_router(validation.router, prefix="/projects/{project_id}/validation", tags=["Validation"])
router.include_router(artifacts.router, prefix="/artifacts", tags=["Artifacts"])
router.include_router(collaboration.router, tags=["Collaboration"])
router.include_router(export.router, tags=["Export"])
router.include_router(verification.router, prefix="/verification", tags=["Verification"])
