"""
Discipline Packs - Subject-specific validation rules.

Each discipline defines:
- Validation mode (HARD/SOFT/WARNING) per artifact type
- Required evidence types
- Citation format requirements
- Defense question templates
"""

from src.plugins.disciplines.base import DisciplinePack, ValidationMode
from src.plugins.disciplines.stem import STEMPack
from src.plugins.disciplines.humanities import HumanitiesPack
from src.plugins.disciplines.social_sciences import SocialSciencesPack
from src.plugins.disciplines.legal import LegalPack

__all__ = [
    "DisciplinePack",
    "ValidationMode",
    "STEMPack",
    "HumanitiesPack",
    "SocialSciencesPack",
    "LegalPack",
]
