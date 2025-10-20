"""Base DTOs and common schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """Base Data Transfer Object with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
    )


class ErrorResponse(BaseDTO):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
