"""
Common schema types used across the API.
"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str
    code: Optional[str] = None
    field: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "ok"
    version: str
    database: str = "connected"
