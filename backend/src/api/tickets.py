import logging
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.config.constants import TicketPriority, TicketStatus, ThreatLevel
from src.services.ticket_service import (
    InvalidStateTransitionError,
    TicketAuthorizationError,
    TicketError,
    TicketNotFoundError,
    TicketService,
)
from src.utils.auth_middleware import get_current_user, get_request_context, require_auth

tickets_bp = Blueprint("tickets", __name__)
ticket_service = TicketService()
logger = logging.getLogger(__name__)


def _serialize_ticket(ticket: Any, include_details: bool = False) -> Dict[str, Any]:
    """Serialize ticket to dict."""
    if include_details:
        # Full details (used in detail view)
        return {
            "id": ticket.get("id"),
            "video_id": ticket.get("video_id"),
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "priority": ticket.get("priority"),
            "status": ticket.get("status"),
            "threat_level": ticket.get("threat_level"),
            "assigned_to": ticket.get("assigned_to"),
            "created_by": ticket.get("created_by"),
            "acknowledged_at": ticket.get("acknowledged_at"),
            "closed_at": ticket.get("closed_at"),
            "escalated": ticket.get("escalated"),
            "escalation_count": ticket.get("escalation_count"),
            "escalation_sent_at": ticket.get("escalation_sent_at"),
            "sla_breach": ticket.get("sla_breach"),
            "auto_close_at": ticket.get("auto_close_at"),
            "created_at": ticket.get("created_at"),
            "updated_at": ticket.get("updated_at"),
            "evidence": ticket.get("evidence", []),
            "persons_of_interest": ticket.get("persons_of_interest", []),
            "history": ticket.get("history", []),
            "video": ticket.get("video"),
            "assigned_user": ticket.get("assigned_user"),
        }
    else:
        # Summary (used in list view)
        return {
            "id": ticket.get("id"),
            "title": ticket.get("title"),
            "status": ticket.get("status"),
            "priority": ticket.get("priority"),
            "threat_level": ticket.get("threat_level"),
            "created_at": ticket.get("created_at"),
            "assigned_to": ticket.get("assigned_to"),
            "evidence_count": ticket.get("evidence_count", 0),
            "person_count": ticket.get("person_count", 0),
        }


@tickets_bp.route("/", methods=["GET"])
@require_auth
def list_tickets():
    """List tickets with pagination and filtering."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        # Get query parameters
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 20)), 100)  # Max 100
        status = request.args.get("status")
        priority = request.args.get("priority")
        assigned_to = request.args.get("assigned_to")
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")
        threat_level = request.args.get("threat_level")

        # Build filters dict
        filters = {}
        if status:
            allowed_status = [TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED]
            if status not in allowed_status:
                return jsonify({"error": "Invalid status value"}), 400
            filters["status"] = status
        if priority:
            allowed_priority = [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.CRITICAL]
            if priority not in allowed_priority:
                return jsonify({"error": "Invalid priority value"}), 400
            filters["priority"] = priority
        if assigned_to:
            # Handle 'none' sentinel value for unassigned tickets
            if assigned_to == 'none':
                filters["assigned_to"] = None
            else:
                filters["assigned_to"] = assigned_to
        if date_from_str:
            try:
                filters["date_from"] = datetime.fromisoformat(date_from_str.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid date_from format (use ISO format)"}), 400
        if date_to_str:
            try:
                filters["date_to"] = datetime.fromisoformat(date_to_str.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid date_to format (use ISO format)"}), 400
        if threat_level:
            allowed_threat_level = [ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL, ThreatLevel.NONE]
            if threat_level not in allowed_threat_level:
                return jsonify({"error": "Invalid threat_level value"}), 400
            filters["threat_level"] = threat_level

        # Validate pagination
        if page < 1:
            return jsonify({"error": "page must be >= 1"}), 400

        # Call service
        result, error = ticket_service.list_tickets(
            filters=filters if filters else None,
            page=page,
            per_page=per_page,
            user_id=user.id,
            user_role=user.role,
        )

        if error:
            logger.error("List tickets failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": "Invalid query parameters"}), 400
    except Exception as exc:
        logger.exception("Unexpected error in list_tickets", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/<ticket_id>", methods=["GET"])
@require_auth
def get_ticket(ticket_id: str):
    """Get ticket details with all relationships."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        # Validate ticket_id format (UUID)
        if len(ticket_id) != 36:
            return jsonify({"error": "Invalid ticket ID format"}), 400

        # Call service
        ticket_dict, error = ticket_service.get_ticket_details(
            ticket_id=ticket_id, user_id=user.id, user_role=user.role
        )

        if error:
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found"}), 404
            elif isinstance(error, TicketAuthorizationError):
                return jsonify({"error": "Forbidden - Not authorized to view this ticket"}), 403
            logger.error("Get ticket failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return jsonify({"ticket": ticket_dict}), 200
    except Exception as exc:
        logger.exception("Unexpected error in get_ticket", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/", methods=["POST"])
@require_auth
def create_ticket():
    """Create new ticket (typically called by AI orchestrator)."""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid JSON payload"}), 400

        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json() or {}
        video_id = data.get("video_id")
        analysis_result = data.get("analysis_result")
        evidence_ids = data.get("evidence_ids", [])
        person_ids = data.get("person_ids", [])

        # Validate request data
        if not video_id:
            return jsonify({"error": "video_id is required"}), 400
        if not analysis_result:
            return jsonify({"error": "analysis_result is required"}), 400

        # Call service
        ticket, error = ticket_service.create_ticket(
            video_id=video_id,
            analysis_result=analysis_result,
            evidence_ids=evidence_ids if evidence_ids else None,
            person_ids=person_ids if person_ids else None,
            created_by_user_id=user.id,
        )

        if error:
            if isinstance(error, TicketNotFoundError) and "Video" in str(error):
                return jsonify({"error": "Video not found"}), 404
            logger.error("Create ticket failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 400

        return (
            jsonify(
                {
                    "message": "Ticket created successfully",
                    "ticket": {
                        "id": ticket.id,
                        "title": ticket.title,
                        "status": ticket.status,
                        "priority": ticket.priority,
                        "threat_level": ticket.threat_level,
                        "auto_close_at": ticket.auto_close_at.isoformat() if ticket.auto_close_at else None,
                    },
                }
            ),
            201,
        )
    except Exception as exc:
        logger.exception("Unexpected error in create_ticket", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/<ticket_id>/acknowledge", methods=["POST"])
@require_auth
def acknowledge_ticket(ticket_id: str):
    """Acknowledge ticket and assign to current user."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        # Call service
        ticket, error = ticket_service.acknowledge_ticket(ticket_id=ticket_id, user_id=user.id)

        if error:
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found"}), 404
            elif isinstance(error, TicketError) and "already" in str(error).lower():
                return jsonify({"error": "Ticket already acknowledged or closed"}), 400
            logger.error("Acknowledge ticket failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return (
            jsonify(
                {
                    "message": "Ticket acknowledged successfully",
                    "ticket": {
                        "id": ticket.id,
                        "status": ticket.status,
                        "acknowledged_at": ticket.acknowledged_at.isoformat()
                        if ticket.acknowledged_at
                        else None,
                        "assigned_to": ticket.assigned_to,
                        "sla_breach": ticket.sla_breach,
                    },
                }
            ),
            200,
        )
    except Exception as exc:
        logger.exception("Unexpected error in acknowledge_ticket", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/<ticket_id>/close", methods=["POST"])
@require_auth
def close_ticket(ticket_id: str):
    """Close ticket with optional reason."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        # Get optional reason from request body
        reason = None
        if request.is_json:
            data = request.get_json() or {}
            reason = data.get("reason")

        # Call service
        ticket, error = ticket_service.close_ticket(ticket_id=ticket_id, user_id=user.id, reason=reason)

        if error:
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found"}), 404
            elif isinstance(error, TicketError) and "already" in str(error).lower():
                return jsonify({"error": "Ticket already closed"}), 400
            logger.error("Close ticket failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return (
            jsonify(
                {
                    "message": "Ticket closed successfully",
                    "ticket": {
                        "id": ticket.id,
                        "status": ticket.status,
                        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                    },
                }
            ),
            200,
        )
    except Exception as exc:
        logger.exception("Unexpected error in close_ticket", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/<ticket_id>/escalate", methods=["POST"])
@require_auth
def escalate_ticket(ticket_id: str):
    """Manually escalate ticket to secondary channel."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        # Get optional reason from request body
        reason = None
        if request.is_json:
            data = request.get_json() or {}
            reason = data.get("reason")

        # Call service
        ticket, error = ticket_service.escalate_ticket(ticket_id=ticket_id, reason=reason)

        if error:
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found"}), 404
            elif isinstance(error, TicketError) and "closed" in str(error).lower():
                return jsonify({"error": "Cannot escalate a closed ticket"}), 400
            logger.error("Escalate ticket failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return (
            jsonify(
                {
                    "message": "Ticket escalated successfully",
                    "ticket": {
                        "id": ticket.id,
                        "escalated": ticket.escalated,
                        "escalation_count": ticket.escalation_count,
                        "escalation_sent_at": ticket.escalation_sent_at.isoformat()
                        if ticket.escalation_sent_at
                        else None,
                    },
                }
            ),
            200,
        )
    except Exception as exc:
        logger.exception("Unexpected error in escalate_ticket", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/<ticket_id>/status", methods=["PATCH"])
@require_auth
def update_status(ticket_id: str):
    """Update ticket status with state machine validation."""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid JSON payload"}), 400

        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json() or {}
        new_status = data.get("status")

        if not new_status:
            return jsonify({"error": "status is required"}), 400

        # Validate status value
        allowed_status = [TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED]
        if new_status not in allowed_status:
            return jsonify({"error": "Invalid status value"}), 400

        # Call service
        ticket, error = ticket_service.update_status(
            ticket_id=ticket_id, new_status=new_status, user_id=user.id
        )

        if error:
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found"}), 404
            elif isinstance(error, InvalidStateTransitionError):
                return jsonify({"error": "Invalid state transition"}), 400
            logger.error("Update status failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return (
            jsonify(
                {
                    "message": "Ticket status updated successfully",
                    "ticket": {"id": ticket.id, "status": ticket.status},
                }
            ),
            200,
        )
    except Exception as exc:
        logger.exception("Unexpected error in update_status", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500


@tickets_bp.route("/<ticket_id>/assign", methods=["PATCH"])
@require_auth
def assign_ticket(ticket_id: str):
    """Assign ticket to user."""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid JSON payload"}), 400

        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json() or {}
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Validate authorization: staff can only assign to themselves, admin can assign to anyone
        if current_user.role != "admin" and user_id != current_user.id:
            return jsonify({"error": "Forbidden - Cannot assign to other users"}), 403

        # Call service
        ticket, error = ticket_service.assign_ticket(
            ticket_id=ticket_id, user_id=user_id, assigned_by_user_id=current_user.id
        )

        if error:
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found or user not found"}), 404
            logger.error("Assign ticket failed", extra={"context": {"error": str(error)}})
            return jsonify({"error": str(error)}), 500

        return (
            jsonify(
                {
                    "message": "Ticket assigned successfully",
                    "ticket": {"id": ticket.id, "assigned_to": ticket.assigned_to},
                }
            ),
            200,
        )
    except Exception as exc:
        logger.exception("Unexpected error in assign_ticket", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500

