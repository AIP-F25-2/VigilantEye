from sqlalchemy import event

from src.models.person import Person
from src.models.video import Video


@event.listens_for(Video, "before_insert")
def apply_video_ttl(mapper, connection, target):  # type: ignore[override]
    """Ensure videos have a TTL when persisted."""
    if getattr(target, "expires_at", None) is None:
        target.set_video_ttl()


@event.listens_for(Person, "before_insert")
def apply_person_ttl(mapper, connection, target):  # type: ignore[override]
    """Ensure persons have a TTL when persisted unless overridden."""
    if getattr(target, "expires_at", None) is None:
        target.set_person_ttl()


@event.listens_for(Person.tickets, "append")
def retain_ticket_linked_person(target, value, initiator):  # type: ignore[override]
    """Retain persons associated with tickets by clearing TTL."""
    if getattr(target, "expires_at", None) is not None:
        target.expires_at = None
    return value


@event.listens_for(Person.tickets, "remove")
def restore_person_ttl(target, value, initiator):  # type: ignore[override]
    """Reapply TTL when a person is no longer linked to any tickets."""
    if not target.tickets:
        target.set_person_ttl()
    return value

