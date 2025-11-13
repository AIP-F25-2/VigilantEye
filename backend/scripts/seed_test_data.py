"""Database seeding script for integration tests and development."""

import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

from src.app import create_app, db
from src.models import (
    AIPerformanceMetrics,
    AuditLog,
    Camera,
    Evidence,
    Person,
    Ticket,
    TicketHistory,
    User,
    Video,
)

fake = Faker()


def seed_users(count=10):
    """Create test users."""
    users = []

    # Create admin users
    admin1 = User(
        username="admin1",
        email="admin1@example.com",
        role="admin",
        is_active=True,
        last_login=datetime.utcnow() - timedelta(hours=1),
    )
    admin1.set_password("admin123")
    db.session.add(admin1)
    users.append(admin1)

    admin2 = User(
        username="admin2",
        email="admin2@example.com",
        role="admin",
        is_active=True,
        last_login=datetime.utcnow() - timedelta(hours=2),
    )
    admin2.set_password("admin123")
    db.session.add(admin2)
    users.append(admin2)

    # Create staff users
    for i in range(count - 2):
        user = User(
            username=f"staff{i+1}",
            email=fake.email(),
            role="staff",
            is_active=True,
            last_login=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
        )
        user.set_password("Password123")
        db.session.add(user)
        users.append(user)

    db.session.commit()
    return users


def seed_cameras(count=5):
    """Create test cameras."""
    cameras = []
    locations = ["Front Entrance", "Parking Lot", "Back Door", "Lobby", "Server Room"]

    for i in range(count):
        camera = Camera(
            name=locations[i] if i < len(locations) else f"Camera {i+1}",
            location=fake.address(),
            stream_url=f"rtsp://192.168.1.{100+i}:554/stream",
            status="active" if i < 3 else "inactive",
            last_active=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
        )
        db.session.add(camera)
        cameras.append(camera)

    db.session.commit()
    return cameras


def seed_videos(users, cameras, count=30):
    """Create test videos."""
    videos = []

    for i in range(count):
        user = random.choice(users)
        upload_type = "upload" if i < 20 else "stream"
        camera = random.choice(cameras) if upload_type == "stream" else None

        filename = f"surveillance_{fake.date_time_this_month().strftime('%Y%m%d_%H%M%S')}.mp4"
        video = Video(
            filename=filename,
            filepath=f"videos/2024/01/15/{filename}",
            user_id=user.id,
            camera_id=camera.id if camera else None,
            upload_type=upload_type,
            status=random.choice(["ready", "ready", "ready", "analyzed", "analyzing", "error"]),
            duration=random.uniform(30, 300),
            fps=30,
            resolution="1920x1080",
            filesize=random.randint(10 * 1024 * 1024, 100 * 1024 * 1024),
            analysis_result=random.choice(["clean", "clean", "clean", "suspicious"]) if i % 3 == 0 else None,
        )
        video.set_video_ttl()
        db.session.add(video)
        videos.append(video)

    db.session.commit()
    return videos


def seed_persons(videos, count=50):
    """Create test persons."""
    persons = []
    suspicious_videos = [v for v in videos if v.analysis_result == "suspicious"]

    for i in range(count):
        if not suspicious_videos:
            break
        video = random.choice(suspicious_videos)
        person = Person(
            video_id=video.id,
            person_tracking_id=f"person_{uuid.uuid4().hex[:8]}",
            first_seen=video.created_at + timedelta(seconds=random.randint(0, int(video.duration or 60))),
            last_seen=video.created_at + timedelta(seconds=random.randint(0, int(video.duration or 60))),
            age_estimate=random.randint(18, 65),
            gender=random.choice(["male", "female"]),
            ethnicity=random.choice(["caucasian", "asian", "african", "hispanic"]),
            confidence_score=random.uniform(0.7, 0.99),
            clothing_description=fake.sentence(),
        )
        person.set_person_ttl()
        db.session.add(person)
        persons.append(person)

    db.session.commit()
    return persons


def seed_tickets(videos, persons, count=15):
    """Create test tickets."""
    tickets = []
    suspicious_videos = [v for v in videos if v.analysis_result == "suspicious"]

    for i in range(count):
        if not suspicious_videos:
            break
        video = random.choice(suspicious_videos)
        priority = random.choices(
            ["critical", "high", "medium", "low"], weights=[0.2, 0.3, 0.4, 0.1]
        )[0]

        ticket = Ticket(
            video_id=video.id,
            title=f"Suspicious Activity Detected at {fake.date_time_this_month()}",
            description=fake.paragraph(),
            priority=priority,
            status=random.choices(
                ["open", "acknowledged", "closed", "in_progress"], weights=[0.4, 0.3, 0.2, 0.1]
            )[0],
            threat_level=priority,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
        )
        ticket.set_auto_close_deadline()

        # Link 2-5 persons to ticket
        ticket_persons_list = random.sample(persons, min(random.randint(2, 5), len(persons)))
        ticket.persons_of_interest = ticket_persons_list

        # Set SLA breach for old tickets
        if ticket.created_at < datetime.utcnow() - timedelta(minutes=15):
            ticket.sla_breach = random.random() < 0.3

        db.session.add(ticket)
        tickets.append(ticket)

    db.session.commit()
    return tickets


def seed_evidence(tickets, videos, count=40):
    """Create test evidence."""
    evidence_list = []

    for ticket in tickets:
        evidence_count = random.randint(2, 3)
        for i in range(evidence_count):
            evidence_type = random.choices(["frame", "audio", "video"], weights=[0.6, 0.3, 0.1])[0]
            filepath = (
                f"evidence/{ticket.id}/frame_{i}.jpg"
                if evidence_type == "frame"
                else f"evidence/{ticket.id}/audio_{i}.wav"
            )

            evidence = Evidence(
                video_id=ticket.video_id,
                ticket_id=ticket.id,
                type=evidence_type,
                filepath=filepath,
                timestamp=ticket.created_at + timedelta(seconds=random.randint(0, 300)),
                frame_number=random.randint(0, 1000) if evidence_type == "frame" else None,
                ai_analysis={
                    "scene": {"scene_type": "outdoor", "lighting": "dark"},
                    "persons": [{"person_id": "person_123", "confidence": 0.89}],
                    "objects": {"objects": [{"class_name": "knife", "threat_level": "high"}]},
                },
                is_flagged=True,
                confidence_score=random.uniform(0.7, 0.99),
            )
            db.session.add(evidence)
            evidence_list.append(evidence)

    db.session.commit()
    return evidence_list


def seed_ticket_history(tickets):
    """Create ticket history entries."""
    for ticket in tickets:
        # All tickets have 'created' event
        history = TicketHistory(
            ticket_id=ticket.id,
            event="created",
            details={"priority": ticket.priority, "threat_level": ticket.threat_level},
            occurred_at=ticket.created_at,
        )
        db.session.add(history)

        # Acknowledged tickets have 'acknowledged' event
        if ticket.status in ["acknowledged", "in_progress", "closed"]:
            history = TicketHistory(
                ticket_id=ticket.id,
                event="acknowledged",
                details={"user_id": str(ticket.assigned_to) if ticket.assigned_to else None},
                occurred_at=ticket.acknowledged_at or ticket.created_at + timedelta(minutes=5),
            )
            db.session.add(history)

        # Closed tickets have 'closed' event
        if ticket.status == "closed":
            history = TicketHistory(
                ticket_id=ticket.id,
                event="closed",
                details={"reason": "Resolved"},
                occurred_at=ticket.closed_at or ticket.created_at + timedelta(hours=2),
            )
            db.session.add(history)

        # 30% of tickets have 'escalated' event
        if random.random() < 0.3:
            history = TicketHistory(
                ticket_id=ticket.id,
                event="escalated",
                details={"escalation_count": ticket.escalation_count or 1},
                occurred_at=ticket.escalation_sent_at or ticket.created_at + timedelta(minutes=10),
            )
            db.session.add(history)

    db.session.commit()


def seed_ai_performance_metrics(videos, count=100):
    """Create AI performance metrics."""
    analyzed_videos = [v for v in videos if v.status == "analyzed"]
    if not analyzed_videos:
        return

    tasks = [
        "person_detection",
        "scene_analysis",
        "object_detection",
        "speech_to_text",
        "audio_classification",
        "llm_analysis",
    ]
    models = ["yolov8n", "blip2-opt-2.7b", "whisper-base", "yamnet", "llama3.2:1b"]

    for i in range(count):
        video = random.choice(analyzed_videos)
        task = random.choice(tasks)
        model = random.choice(models)

        # Realistic duration values
        duration_map = {
            "person_detection": (100, 200),
            "scene_analysis": (400, 600),
            "object_detection": (200, 400),
            "speech_to_text": (25000, 35000),
            "audio_classification": (500, 1000),
            "llm_analysis": (400, 600),
        }
        duration_range = duration_map.get(task, (100, 1000))
        duration_ms = random.randint(duration_range[0], duration_range[1])

        metric = AIPerformanceMetrics(
            video_id=video.id,
            task_name=task,
            model_name=model,
            duration_ms=duration_ms,
            status="success" if random.random() < 0.95 else "failure",
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 7)),
        )
        db.session.add(metric)

    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Seeding database...")

        users = seed_users()
        cameras = seed_cameras()
        videos = seed_videos(users, cameras)
        persons = seed_persons(videos)
        tickets = seed_tickets(videos, persons)
        evidence = seed_evidence(tickets, videos)
        seed_ticket_history(tickets)
        seed_ai_performance_metrics(videos)

        print(
            f"Seeded: {len(users)} users, {len(cameras)} cameras, {len(videos)} videos, "
            f"{len(persons)} persons, {len(tickets)} tickets, {len(evidence)} evidence"
        )
