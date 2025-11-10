import uuid
from datetime import datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.app import db


def generate_uuid() -> str:
    """Return a new UUID4 string."""
    return str(uuid.uuid4())


class BaseModel(db.Model):  # type: ignore[misc]
    """Declarative base mixin providing common columns and helpers."""

    __abstract__ = True
    __allow_unmapped__ = True

    id = Column(
        CHAR(36),
        primary_key=True,
        default=generate_uuid,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    is_deleted = Column(Boolean, nullable=False, default=False)

    def soft_delete(self) -> None:
        """Mark instance as deleted without removing from the database."""
        setattr(self, "is_deleted", True)

    def to_dict(self, exclude: Iterable[str] | None = None) -> dict[str, Any]:
        """Serialize model attributes into a dictionary, skipping excluded fields."""
        excluded = set(exclude or [])
        data: dict[str, Any] = {}
        for column in self.__table__.columns:  # type: ignore[attr-defined]
            name = column.name
            if name in excluded:
                continue
            value = getattr(self, name)
            if isinstance(value, datetime):
                data[name] = value.isoformat()
            else:
                data[name] = value
        return data


class TTLMixin:
    """Mixin providing TTL support through expires_at."""

    __abstract__ = True
    __allow_unmapped__ = True

    @declared_attr
    def expires_at(cls) -> Mapped[datetime]:  # type: ignore[override]
        return mapped_column(DateTime, nullable=True, index=True)

    def is_expired(self) -> bool:
        """Return True if the resource has expired."""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.utcnow()

    def set_ttl(self, hours: int | float) -> None:
        """Set expires_at relative to created_at using supplied hours."""
        if hours is None:
            self.expires_at = None
            return
        base_time = getattr(self, "created_at", None) or datetime.utcnow()
        self.expires_at = base_time + timedelta(hours=float(hours))

