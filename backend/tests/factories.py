"""Factory classes for generating test data using factory-boy."""

import factory
from datetime import datetime, timedelta
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from src.app import db
from src.models import (
    Camera,
    Evidence,
    Person,
    Ticket,
    TicketHistory,
    User,
    Video,
)

fake = Faker()


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configuration."""

    class Meta:
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    """Factory for User model."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    role = "staff"
    is_active = True
    password_hash = factory.PostGeneration(
        lambda obj, create, extracted: obj.set_password(extracted or "Password123")
    )

    class Params:
        admin = factory.Trait(role="admin")
        inactive = factory.Trait(is_active=False)


class CameraFactory(BaseFactory):
    """Factory for Camera model."""

    class Meta:
        model = Camera

    name = factory.Faker("word")
    location = factory.Faker("address")
    stream_url = factory.Sequence(lambda n: f"rtsp://192.168.1.{100+n}:554/stream")
    status = "active"

    class Params:
        inactive = factory.Trait(status="inactive")


class VideoFactory(BaseFactory):
    """Factory for Video model."""

    class Meta:
        model = Video

    filename = factory.Faker("file_name", extension="mp4")
    filepath = factory.LazyAttribute(lambda obj: f"videos/2024/01/15/{obj.filename}")
    user = factory.SubFactory(UserFactory)
    camera = factory.SubFactory(CameraFactory)  # nullable
    upload_type = "upload"
    status = "ready"
    duration = factory.Faker("pyfloat", min_value=30, max_value=300)
    fps = 30
    resolution = "1920x1080"
    filesize = factory.Faker("pyint", min_value=10000000, max_value=100000000)

    @factory.post_generation
    def set_ttl(self, create, extracted, **kwargs):
        """Set video TTL after creation."""
        if create:
            self.set_video_ttl()

    class Params:
        analyzed = factory.Trait(status="analyzed", analysis_result="clean")
        suspicious = factory.Trait(analysis_result="suspicious")
        streamed = factory.Trait(upload_type="stream")


class PersonFactory(BaseFactory):
    """Factory for Person model."""

    class Meta:
        model = Person

    video = factory.SubFactory(VideoFactory)
    person_tracking_id = factory.Sequence(lambda n: f"person_{n:04d}")
    first_seen = factory.LazyFunction(datetime.utcnow)
    last_seen = factory.LazyFunction(datetime.utcnow)
    age_estimate = factory.Faker("pyint", min_value=18, max_value=65)
    gender = factory.Faker("random_element", elements=["male", "female"])
    ethnicity = factory.Faker(
        "random_element", elements=["caucasian", "asian", "african", "hispanic"]
    )
    confidence_score = factory.Faker("pyfloat", min_value=0.7, max_value=0.99)
    clothing_description = factory.Faker("sentence")

    @factory.post_generation
    def set_ttl(self, create, extracted, **kwargs):
        """Set person TTL after creation."""
        if create:
            self.set_person_ttl()


class TicketFactory(BaseFactory):
    """Factory for Ticket model."""

    class Meta:
        model = Ticket

    video = factory.SubFactory(VideoFactory)
    title = factory.Faker("sentence")
    description = factory.Faker("paragraph")
    priority = "medium"
    status = "open"
    threat_level = "medium"
    assigned_to = None  # nullable
    created_by = None  # nullable

    @factory.post_generation
    def set_auto_close(self, create, extracted, **kwargs):
        """Set auto-close deadline after creation."""
        if create:
            self.set_auto_close_deadline()

    class Params:
        acknowledged = factory.Trait(
            status="acknowledged",
            assigned_to=factory.SubFactory(UserFactory),
            acknowledged_at=factory.LazyFunction(datetime.utcnow),
        )
        closed = factory.Trait(
            status="closed",
            closed_at=factory.LazyFunction(datetime.utcnow),
        )
        critical = factory.Trait(priority="critical", threat_level="critical")
        high = factory.Trait(priority="high", threat_level="high")


class EvidenceFactory(BaseFactory):
    """Factory for Evidence model."""

    class Meta:
        model = Evidence

    video = factory.SubFactory(VideoFactory)
    ticket = factory.SubFactory(TicketFactory)
    type = "frame"
    filepath = factory.LazyAttribute(
        lambda obj: f"evidence/{obj.ticket_id}/frame_{factory.Faker('pyint').generate()}.jpg"
    )
    timestamp = factory.LazyFunction(datetime.utcnow)
    frame_number = factory.Sequence(lambda n: n)
    ai_analysis = factory.Dict(
        {
            "scene": {"scene_type": "outdoor", "lighting": "dark"},
            "persons": [{"person_id": "person_123", "confidence": 0.89}],
        }
    )
    is_flagged = True
    confidence_score = factory.Faker("pyfloat", min_value=0.7, max_value=0.99)

    class Params:
        audio = factory.Trait(
            type="audio",
            filepath=factory.LazyAttribute(
                lambda obj: f"evidence/{obj.ticket_id}/audio_{factory.Faker('pyint').generate()}.wav"
            ),
        )
        video_evidence = factory.Trait(
            type="video",
            filepath=factory.LazyAttribute(
                lambda obj: f"evidence/{obj.ticket_id}/video_{factory.Faker('pyint').generate()}.mp4"
            ),
        )


class TicketHistoryFactory(BaseFactory):
    """Factory for TicketHistory model."""

    class Meta:
        model = TicketHistory

    ticket = factory.SubFactory(TicketFactory)
    event = "created"
    details = factory.Dict({"key": "value"})
    occurred_at = factory.LazyFunction(datetime.utcnow)

    class Params:
        acknowledged = factory.Trait(
            event="acknowledged",
            details=factory.Dict({"user_id": factory.LazyAttribute(lambda obj: str(obj.ticket.assigned_to))}),
        )
        closed = factory.Trait(
            event="closed",
            details=factory.Dict({"reason": "Resolved"}),
        )
        escalated = factory.Trait(
            event="escalated",
            details=factory.Dict({"escalation_count": 1}),
        )
