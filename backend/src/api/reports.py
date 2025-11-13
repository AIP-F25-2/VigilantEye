import logging
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from src.app import db
from src.models.audit_log import AuditLog
from src.services.report_service import ReportError, ReportService
from src.services.ticket_service import TicketAuthorizationError, TicketNotFoundError
from src.utils.auth_middleware import get_current_user, require_auth

reports_bp = Blueprint("reports", __name__)
report_service = ReportService()
logger = logging.getLogger(__name__)


@reports_bp.route("/tickets/<ticket_id>/report/download", methods=["GET"])
@require_auth
def download_report(ticket_id: str):
    """Download security incident report in PDF or JSON format."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Unauthorized"}), 401

        # Get format parameter (default: pdf)
        format_param = request.args.get("format", "pdf").lower()
        if format_param not in ["pdf", "json"]:
            return jsonify({"error": "Invalid format. Must be 'pdf' or 'json'"}), 400

        # Generate report
        report_bytes, error = report_service.generate_report(
            ticket_id=ticket_id,
            format=format_param,
            user_id=current_user.id,
            user_role=current_user.role,
        )

        if error:
            if isinstance(error, ReportError):
                return jsonify({"error": str(error)}), 400
            if isinstance(error, TicketNotFoundError):
                return jsonify({"error": "Ticket not found"}), 404
            if isinstance(error, TicketAuthorizationError):
                return jsonify({"error": "Forbidden - Not authorized to view this ticket"}), 403
            logger.error(
                "Report generation failed",
                extra={"context": {"ticket_id": ticket_id, "error": str(error)}},
            )
            return jsonify({"error": "Failed to generate report"}), 500

        if not report_bytes:
            return jsonify({"error": "Report generation returned empty result"}), 500

        # Create filename
        filename = f"VigilentEye_Report_{ticket_id[:8]}.{format_param}"

        # Determine mimetype
        mimetype = "application/pdf" if format_param == "pdf" else "application/json"

        # Create audit log
        try:
            audit_log = AuditLog(
                user_id=current_user.id,
                action="report_downloaded",
                resource_type="ticket",
                resource_id=ticket_id,
                details={
                    "format": format_param,
                    "filename": filename,
                },
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as audit_exc:
            logger.warning(
                "Failed to create audit log for report download",
                extra={"context": {"ticket_id": ticket_id, "error": str(audit_exc)}},
            )

        # Return file
        return send_file(
            BytesIO(report_bytes),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
        )

    except Exception as exc:
        logger.exception(
            "Unexpected error in download_report",
            extra={"context": {"ticket_id": ticket_id, "error": str(exc)}},
        )
        return jsonify({"error": "Internal server error"}), 500

