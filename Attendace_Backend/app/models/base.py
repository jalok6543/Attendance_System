"""Base model and common fields."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base Pydantic schema with common config."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for created_at timestamp."""

    created_at: datetime | None = None


class AuditMixin(TimestampMixin):
    """Mixin for audit fields."""

    updated_at: datetime | None = None
