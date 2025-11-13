import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import redis
from sqlalchemy.orm import joinedload

from src.app import db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel
from src.config.settings import get_config
from src.models.audit_log import AuditLog
from src.models.evidence import Evidence
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.user import User
from src.models.video import Video
from src.services.messenger_service import MessengerService
from src.services.report_cache import invalidate_report_cache
from src.utils.db_utils import retry_on_db_error

logger = logging.getLogger(__name__)


class TicketError(Exception):
    """Base exception for ticket operations."""


class TicketNotFoundError(TicketError):
    """Raised when ticket doesn't exist."""


class InvalidStateTransitionError(TicketError):
    """Raised when invalid state machine transition is attempted."""


class TicketAuthorizationError(TicketError):
    """Raised when user is not authorized for operation."""


class TicketService:
    """Service layer responsible for ticket management workflows."""

    def __init__(self, config=None):
        self.config = config or get_config()
        try:
            self.redis_client = redis.from_url(
                self.config.REDIS_URL,
                decode_responses=True,
            )
        except redis.RedisError as exc:
            logger.warning("Redis connection failed: %s", exc)
            self.redis_client = None
        try:
            self.messenger_service = MessengerService(config=self.config)
        except Exception as exc:
            logger.warning("Failed to initialize MessengerService: %s", exc)
            self.messenger_service = None

    @retry_on_db_error()
    def create_ticket(
        self,
        video_id: str,
        analysis_result: Dict,
        evidence_ids: List[str] = None,
        person_ids: List[str] = None,
        created_by_user_id: str = None,
    ) -> Tuple[Optional[Ticket], Optional[Exception]]:
        """Create ticket from AI analysis, link evidence and persons."""
        try:
            # Validate video exists
            video = Video.query.get(video_id)
            if not video:
                return None, TicketNotFoundError("Video not found")

            # Extract data from analysis_result
            threat_level_raw = analysis_result.get("threat_level", "medium")
            reasoning = analysis_result.get("reasoning", "")
            key_factors = analysis_result.get("key_factors", [])

            # Normalize threat_level to valid constant
            threat_level_normalized = threat_level_raw.lower() if threat_level_raw else "medium"
            valid_threat_levels = {ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL}
            if threat_level_normalized not in valid_threat_levels:
                threat_level_normalized = ThreatLevel.MEDIUM
            threat_level = threat_level_normalized

            # Determine priority from threat_level
            threat_to_priority = {
                ThreatLevel.CRITICAL: TicketPriority.CRITICAL,
                ThreatLevel.HIGH: TicketPriority.HIGH,
                ThreatLevel.MEDIUM: TicketPriority.MEDIUM,
                ThreatLevel.LOW: TicketPriority.LOW,
            }
            priority = threat_to_priority.get(threat_level, TicketPriority.MEDIUM)

            # Generate title
            title = f"Suspicious Activity Detected at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

            # Create Ticket instance
            ticket = Ticket(
                video_id=video_id,
                title=title,
                description=reasoning,
                priority=priority,
                status=TicketStatus.OPEN,
                threat_level=threat_level,
                created_by=created_by_user_id,
            )
            ticket.set_auto_close_deadline()
            db.session.add(ticket)
            db.session.flush()  # Get ticket.id

            # Link evidence if provided
            if evidence_ids:
                for evidence_id in evidence_ids:
                    evidence = Evidence.query.get(evidence_id)
                    if evidence:
                        evidence.ticket_id = ticket.id
                        # Clear TTL (permanent storage)
                        evidence.expires_at = None

            # Link persons if provided
            if person_ids:
                for person_id in person_ids:
                    person = Person.query.get(person_id)
                    if person:
                        ticket.persons_of_interest.append(person)
                        # Calculate relevance_score (default 1.0)
                        # Note: relevance_score is stored in association table
                        # This would need to be set via association object if needed

            # Create TicketHistory entry
            self._create_history_entry(
                ticket_id=ticket.id,
                event="created",
                details={
                    "threat_level": threat_level,
                    "key_factors": key_factors,
                },
            )

            # Commit to database
            db.session.commit()

            # Create audit log
            self._create_audit_log(
                user_id=created_by_user_id,
                action="ticket_created",
                resource_id=ticket.id,
                details={
                    "ticket_id": ticket.id,
                    "video_id": video_id,
                    "threat_level": threat_level,
                    "priority": priority,
                },
            )

            # Send initial alert via messenger service (non-blocking)
            # Note: The AI orchestrator may also trigger alerts, but we send here
            # to ensure alerts are sent even if orchestrator doesn't handle it.
            # Failures in alert sending do not block ticket creation.
            if self.messenger_service:
                try:
                    # Find first evidence image if available for alert attachment
                    image_path = None
                    if ticket.evidence:
                        for evidence in ticket.evidence:
                            if evidence.type == "frame" and evidence.filepath:
                                image_path = evidence.filepath
                                break
                    
                    self.messenger_service.send_alert(
                        ticket=ticket,
                        image_path=image_path,
                    )
                except Exception as exc:
                    # Log but don't fail ticket creation if alert fails
                    logger.warning(
                        "Failed to send initial alert for ticket",
                        extra={
                            "context": {
                                "ticket_id": ticket.id,
                                "error": str(exc),
                            }
                        },
                    )

            return ticket, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to create ticket: %s", exc)
            return None, exc

    @retry_on_db_error()
    def acknowledge_ticket(
        self, ticket_id: str, user_id: str
    ) -> Tuple[Optional[Ticket], Optional[Exception]]:
        """Acknowledge ticket and assign to user."""
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return None, TicketNotFoundError("Ticket not found")

            # Validate current status
            if ticket.status != TicketStatus.OPEN:
                return None, TicketError("Ticket already acknowledged or closed")

            # Call ticket model method
            ticket.acknowledge(user_id)

            # Check if SLA was breached
            was_breached = ticket.check_sla_breach()

            # Create TicketHistory entry
            self._create_history_entry(
                ticket_id=ticket.id,
                event="acknowledged",
                details={
                    "acknowledged_by": user_id,
                    "sla_breach": was_breached,
                    "response_time_seconds": ticket.get_response_time(),
                },
            )

            # Commit to database
            db.session.commit()

            # Invalidate report cache
            try:
                invalidate_report_cache(ticket.id, config=self.config)
            except Exception as cache_exc:
                logger.warning(
                    "Failed to invalidate report cache",
                    extra={"context": {"ticket_id": ticket.id, "error": str(cache_exc)}},
                )

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action="ticket_acknowledged",
                resource_id=ticket.id,
                details={
                    "ticket_id": ticket.id,
                    "sla_breach": was_breached,
                },
            )

            return ticket, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to acknowledge ticket: %s", exc)
            return None, exc

    @retry_on_db_error()
    def close_ticket(
        self, ticket_id: str, user_id: str = None, reason: str = None
    ) -> Tuple[Optional[Ticket], Optional[Exception]]:
        """Close ticket with optional reason."""
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return None, TicketNotFoundError("Ticket not found")

            # Validate can close
            if ticket.status == TicketStatus.CLOSED:
                return None, TicketError("Ticket already closed")

            # Call ticket model method
            ticket.close(user_id)

            # Create TicketHistory entry
            self._create_history_entry(
                ticket_id=ticket.id,
                event="closed",
                details={
                    "closed_by": user_id,
                    "reason": reason,
                    "resolution_time_seconds": ticket.get_resolution_time(),
                },
            )

            # Commit to database
            db.session.commit()

            # Invalidate report cache
            try:
                invalidate_report_cache(ticket.id, config=self.config)
            except Exception as cache_exc:
                logger.warning(
                    "Failed to invalidate report cache",
                    extra={"context": {"ticket_id": ticket.id, "error": str(cache_exc)}},
                )

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action="ticket_closed",
                resource_id=ticket.id,
                details={
                    "ticket_id": ticket.id,
                    "reason": reason,
                },
            )

            return ticket, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to close ticket: %s", exc)
            return None, exc

    @retry_on_db_error()
    def escalate_ticket(
        self, ticket_id: str, reason: str = None
    ) -> Tuple[Optional[Ticket], Optional[Exception]]:
        """Escalate ticket to secondary channel."""
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return None, TicketNotFoundError("Ticket not found")

            # Guard: cannot escalate closed tickets
            if ticket.status == TicketStatus.CLOSED:
                return None, TicketError("Cannot escalate a closed ticket")

            # Call ticket model method
            ticket.escalate()

            # Create TicketHistory entry
            self._create_history_entry(
                ticket_id=ticket.id,
                event="escalated",
                details={
                    "reason": reason,
                    "escalation_count": ticket.escalation_count,
                },
            )

            # Commit to database
            db.session.commit()

            # Send escalation alert via messenger service (stub for now)
            if self.messenger_service:
                try:
                    self.messenger_service.send_escalation_alert(ticket)
                except Exception as exc:
                    logger.warning(
                        "Failed to send escalation alert via messenger service: %s", exc
                    )

            # Create audit log
            self._create_audit_log(
                user_id=None,
                action="ticket_escalated",
                resource_id=ticket.id,
                details={
                    "ticket_id": ticket.id,
                    "reason": reason,
                    "escalation_count": ticket.escalation_count,
                },
            )

            return ticket, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to escalate ticket: %s", exc)
            return None, exc

    def get_ticket_details(
        self, ticket_id: str, user_id: str = None, user_role: str = None
    ) -> Tuple[Optional[Dict], Optional[Exception]]:
        """Get ticket details with all relationships."""
        try:
            # Query ticket with eager loading
            ticket = (
                Ticket.query.options(
                    joinedload(Ticket.evidence),
                    joinedload(Ticket.persons_of_interest),
                    joinedload(Ticket.history),
                    joinedload(Ticket.video),
                    joinedload(Ticket.assigned_user),
                )
                .filter_by(id=ticket_id, is_deleted=False)
                .first()
            )

            if not ticket:
                return None, TicketNotFoundError("Ticket not found")

            # Check authorization
            if user_role != "admin" and ticket.assigned_to != user_id:
                return None, TicketAuthorizationError(
                    "Forbidden - Not authorized to view this ticket"
                )

            # Build detailed dict
            ticket_dict = {
                "id": ticket.id,
                "video_id": ticket.video_id,
                "title": ticket.title,
                "description": ticket.description,
                "priority": ticket.priority,
                "status": ticket.status,
                "threat_level": ticket.threat_level,
                "assigned_to": ticket.assigned_to,
                "created_by": ticket.created_by,
                "acknowledged_at": ticket.acknowledged_at.isoformat() if ticket.acknowledged_at else None,
                "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                "escalated": ticket.escalated,
                "escalation_count": ticket.escalation_count,
                "escalation_sent_at": ticket.escalation_sent_at.isoformat()
                if ticket.escalation_sent_at
                else None,
                "sla_breach": ticket.sla_breach,
                "auto_close_at": ticket.auto_close_at.isoformat() if ticket.auto_close_at else None,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "evidence": [
                    {
                        "id": ev.id,
                        "type": ev.type,
                        "filepath": ev.filepath,
                        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                        "frame_number": ev.frame_number,
                        "description": ev.description,
                        "ai_analysis": json.loads(ev.ai_analysis) if (ev.ai_analysis and isinstance(ev.ai_analysis, str)) else (ev.ai_analysis if ev.ai_analysis else None),
                        "confidence_score": ev.confidence_score,
                    }
                    for ev in ticket.evidence
                ],
                "persons_of_interest": [
                    {
                        "id": person.id,
                        "person_tracking_id": person.person_tracking_id,
                        "age_estimate": person.age_estimate,
                        "gender": person.gender,
                        "ethnicity": person.ethnicity,
                        "clothing_description": person.clothing_description,
                        "thumbnail_path": person.thumbnail_path,
                    }
                    for person in ticket.persons_of_interest
                ],
                "history": [
                    {
                        "id": hist.id,
                        "event": hist.event,
                        "details": json.loads(hist.details) if (hist.details and isinstance(hist.details, str)) else (hist.details if hist.details else None),
                        "occurred_at": hist.occurred_at.isoformat() if hist.occurred_at else None,
                    }
                    for hist in sorted(ticket.history, key=lambda h: h.occurred_at, reverse=True)
                ],
            }

            # Include video metadata if available
            if ticket.video:
                ticket_dict["video"] = {
                    "id": ticket.video.id,
                    "filename": ticket.video.filename,
                    "duration": ticket.video.duration,
                    "status": ticket.video.status,
                }

            # Include assigned_user details if assigned
            if ticket.assigned_user:
                ticket_dict["assigned_user"] = {
                    "id": ticket.assigned_user.id,
                    "username": ticket.assigned_user.username,
                    "email": ticket.assigned_user.email,
                }

            return ticket_dict, None
        except Exception as exc:
            logger.exception("Failed to get ticket details: %s", exc)
            return None, exc

    def list_tickets(
        self,
        filters: Dict = None,
        page: int = 1,
        per_page: int = 20,
        user_id: str = None,
        user_role: str = None,
    ) -> Tuple[Optional[Dict], Optional[Exception]]:
        """List tickets with filters and pagination."""
        try:
            # Build base query
            query = Ticket.query.filter_by(is_deleted=False)

            # Apply authorization
            if user_role == "admin":
                # Admin sees all tickets
                pass
            elif user_role == "staff":
                # Staff sees only assigned tickets
                query = query.filter_by(assigned_to=user_id)
            else:
                # No role or unknown role - no tickets
                return {"tickets": [], "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0}}, None

            # Apply filters if provided
            if filters:
                if "status" in filters:
                    query = query.filter_by(status=filters["status"])
                if "priority" in filters:
                    query = query.filter_by(priority=filters["priority"])
                if "assigned_to" in filters:
                    # Handle None for unassigned tickets
                    if filters["assigned_to"] is None:
                        query = query.filter(Ticket.assigned_to.is_(None))
                    else:
                        query = query.filter_by(assigned_to=filters["assigned_to"])
                if "date_from" in filters:
                    query = query.filter(Ticket.created_at >= filters["date_from"])
                if "date_to" in filters:
                    query = query.filter(Ticket.created_at <= filters["date_to"])
                if "threat_level" in filters:
                    query = query.filter_by(threat_level=filters["threat_level"])

            # Order by
            query = query.order_by(Ticket.created_at.desc())

            # Eager load relationships to avoid N+1 queries
            query = query.options(
                joinedload(Ticket.evidence),
                joinedload(Ticket.persons_of_interest),
                joinedload(Ticket.assigned_user)
            )

            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            # Serialize tickets
            tickets = []
            for ticket in pagination.items:
                ticket_data = {
                    "id": ticket.id,
                    "title": ticket.title,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "threat_level": ticket.threat_level,
                    "created_at": ticket.created_at.isoformat(),
                    "assigned_to": ticket.assigned_to,
                    "evidence_count": len(ticket.evidence) if ticket.evidence else 0,
                    "person_count": len(ticket.persons_of_interest) if ticket.persons_of_interest else 0,
                }
                # Include assigned_user if present (lightweight: only id and username)
                if ticket.assigned_user:
                    ticket_data["assigned_user"] = {
                        "id": ticket.assigned_user.id,
                        "username": ticket.assigned_user.username,
                    }
                else:
                    ticket_data["assigned_user"] = None
                tickets.append(ticket_data)

            return (
                {
                    "tickets": tickets,
                    "pagination": {
                        "page": pagination.page,
                        "per_page": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                    },
                },
                None,
            )
        except Exception as exc:
            logger.exception("Failed to list tickets: %s", exc)
            return None, exc

    @retry_on_db_error()
    def assign_ticket(
        self, ticket_id: str, user_id: str, assigned_by_user_id: str
    ) -> Tuple[Optional[Ticket], Optional[Exception]]:
        """Assign ticket to user."""
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return None, TicketNotFoundError("Ticket not found")

            user = User.query.get(user_id)
            if not user:
                return None, TicketNotFoundError("User not found")

            # Update assignment
            ticket.assigned_to = user_id

            # Create TicketHistory entry
            self._create_history_entry(
                ticket_id=ticket.id,
                event="assigned",
                details={
                    "assigned_to": user_id,
                    "assigned_by": assigned_by_user_id,
                },
            )

            # Commit to database
            db.session.commit()

            # Create audit log
            self._create_audit_log(
                user_id=assigned_by_user_id,
                action="ticket_assigned",
                resource_id=ticket.id,
                details={
                    "ticket_id": ticket.id,
                    "assigned_to": user_id,
                },
            )

            return ticket, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to assign ticket: %s", exc)
            return None, exc

    @retry_on_db_error()
    def update_status(
        self, ticket_id: str, new_status: str, user_id: str
    ) -> Tuple[Optional[Ticket], Optional[Exception]]:
        """Update ticket status with state machine validation."""
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                return None, TicketNotFoundError("Ticket not found")

            # Validate state transition
            old_status = ticket.status
            if not self._validate_state_transition(old_status, new_status):
                return None, InvalidStateTransitionError(
                    f"Invalid state transition from {old_status} to {new_status}"
                )

            # Update status
            ticket.status = new_status

            # If transitioning to CLOSED, also set closed_at
            if new_status == TicketStatus.CLOSED and not ticket.closed_at:
                ticket.closed_at = datetime.utcnow()

            # Create TicketHistory entry
            self._create_history_entry(
                ticket_id=ticket.id,
                event="status_changed",
                details={
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by": user_id,
                },
            )

            # Commit to database
            db.session.commit()

            # Invalidate report cache
            try:
                invalidate_report_cache(ticket.id, config=self.config)
            except Exception as cache_exc:
                logger.warning(
                    "Failed to invalidate report cache",
                    extra={"context": {"ticket_id": ticket.id, "error": str(cache_exc)}},
                )

            # Create audit log
            self._create_audit_log(
                user_id=user_id,
                action="ticket_status_updated",
                resource_id=ticket.id,
                details={
                    "ticket_id": ticket.id,
                    "old_status": old_status,
                    "new_status": new_status,
                },
            )

            return ticket, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to update ticket status: %s", exc)
            return None, exc

    def _validate_state_transition(self, current_status: str, new_status: str) -> bool:
        """Validate state machine transition."""
        valid_transitions = {
            TicketStatus.OPEN: [TicketStatus.ACKNOWLEDGED, TicketStatus.CLOSED],
            TicketStatus.ACKNOWLEDGED: [
                TicketStatus.IN_PROGRESS,
                TicketStatus.CLOSED,
            ],
            TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED, TicketStatus.CLOSED],
            TicketStatus.RESOLVED: [TicketStatus.CLOSED],
            TicketStatus.CLOSED: [],  # Cannot transition from closed
        }

        if current_status not in valid_transitions:
            return False

        return new_status in valid_transitions[current_status]

    def _create_history_entry(
        self, ticket_id: str, event: str, details: Dict = None
    ) -> None:
        """Create TicketHistory entry for audit trail."""
        history = TicketHistory(
            ticket_id=ticket_id,
            event=event,
            details=json.dumps(details) if details else None,
            occurred_at=datetime.utcnow(),
        )
        db.session.add(history)

    def _create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_id: str,
        details: Dict,
        status: str = "success",
        error_message: str = None,
    ) -> None:
        """Create AuditLog entry (separate transaction to not fail main operation)."""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="ticket",
                resource_id=resource_id,
                details=details,
                status=status,
                error_message=error_message,
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.warning("Failed to create audit log: %s", exc)

