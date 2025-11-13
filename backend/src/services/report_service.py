import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import redis
from jinja2 import Environment, FileSystemLoader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.frames import Frame
from reportlab.platypus.pageTemplate import PageTemplate

from src.ai_modules.person_detector import PersonDetectorService
from src.config.settings import get_config
from src.services.storage_service import StorageService
from src.services.ticket_service import TicketService
from src.utils.db_utils import retry_on_db_error

logger = logging.getLogger(__name__)


class ReportError(Exception):
    """Base exception for report operations."""


class ReportService:
    """Service layer responsible for report generation."""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.storage_base_path = Path(self.config.STORAGE_BASE_PATH).resolve()
        self.cache_ttl = self.config.REPORT_CACHE_TTL_SECONDS
        self.include_similar_persons = self.config.REPORT_INCLUDE_SIMILAR_PERSONS
        self.similar_persons_time_window = self.config.REPORT_SIMILAR_PERSONS_TIME_WINDOW
        self.similar_persons_top_k = self.config.REPORT_SIMILAR_PERSONS_TOP_K
        # Map page size string to ReportLab constant
        page_size_map = {
            "letter": letter,
            "a4": A4,
        }
        self.page_size = page_size_map.get(self.config.REPORT_PAGE_SIZE.lower(), letter)
        self.font_name = self.config.REPORT_FONT_NAME

        try:
            self.redis_client = redis.from_url(
                self.config.REDIS_URL,
                decode_responses=False,  # Binary data for PDF/JSON
            )
        except redis.RedisError as exc:
            logger.warning("Redis connection failed: %s", exc)
            self.redis_client = None

        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates" / "reports"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        
        # Register tojson filter for Jinja2 templates
        def tojson_filter(value):
            """Serialize Python objects to JSON string."""
            return json.dumps(value, ensure_ascii=False, default=str)
        self.jinja_env.filters['tojson'] = tojson_filter

        # Initialize services
        self.ticket_service = TicketService(config=self.config)
        self.person_detector = PersonDetectorService(config=self.config)
        self.storage_service = StorageService(config=self.config)

    @retry_on_db_error()
    def generate_report(
        self,
        ticket_id: str,
        format: str = "pdf",
        user_id: str = None,
        user_role: str = None,
    ) -> Tuple[Optional[bytes], Optional[Exception]]:
        """Generate report in specified format (pdf or json)."""
        try:
            # Check cache first
            cache_key = f"report:{ticket_id}:{format}"
            if self.redis_client:
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.info(
                        "Report cache hit",
                        extra={"context": {"ticket_id": ticket_id, "format": format}},
                    )
                    return cached, None

            # Get ticket details (includes authorization check)
            ticket_dict, error = self.ticket_service.get_ticket_details(
                ticket_id, user_id, user_role
            )
            if error:
                return None, error

            # Aggregate additional data
            evidence_list = ticket_dict.get("evidence", [])
            persons_list = ticket_dict.get("persons_of_interest", [])

            # Parse AI analysis from evidence
            ai_analysis = self._parse_ai_analysis(evidence_list)

            # Get similar persons if enabled
            similar_persons_data = []
            if self.include_similar_persons and persons_list:
                similar_persons_data = self._get_similar_persons(persons_list)

            # Generate executive summary
            executive_summary = self._generate_executive_summary(ticket_dict)

            # Build complete report data
            report_data = {
                "ticket": ticket_dict,
                "evidence": evidence_list,
                "persons": persons_list,
                "similar_persons": similar_persons_data,
                "history": ticket_dict.get("history", []),
                "ai_analysis": ai_analysis,
                "executive_summary": executive_summary,
                "generated_at": datetime.utcnow().isoformat(),
                "generated_by": user_id,
            }

            # Generate report based on format
            if format == "pdf":
                report_bytes = self._generate_pdf_report(report_data)
            elif format == "json":
                report_bytes = self._generate_json_report(report_data).encode("utf-8")
            else:
                return None, ReportError(f"Unsupported format: {format}")

            # Cache the result
            if self.redis_client and report_bytes:
                try:
                    self.redis_client.setex(cache_key, self.cache_ttl, report_bytes)
                except Exception as cache_exc:
                    logger.warning(
                        "Failed to cache report",
                        extra={"context": {"ticket_id": ticket_id, "error": str(cache_exc)}},
                    )

            return report_bytes, None

        except Exception as exc:
            logger.exception(
                "Failed to generate report",
                extra={"context": {"ticket_id": ticket_id, "format": format, "error": str(exc)}},
            )
            return None, exc

    def _get_similar_persons(self, persons: List[Dict]) -> List[Dict]:
        """Get similar persons for each person using ChromaDB."""
        similar_persons_data = []
        for person in persons:
            person_id = person.get("id")
            if not person_id:
                continue

            try:
                similar_persons, error = self.person_detector.find_similar_persons(
                    person_id=person_id,
                    time_window_hours=self.similar_persons_time_window,
                    top_k=self.similar_persons_top_k,
                )
                if error:
                    logger.warning(
                        "Failed to find similar persons",
                        extra={"context": {"person_id": person_id, "error": str(error)}},
                    )
                    similar_persons = []

                similar_persons_data.append(
                    {
                        "person": person,
                        "similar_persons": similar_persons,
                    }
                )
            except Exception as exc:
                logger.warning(
                    "Error finding similar persons",
                    extra={"context": {"person_id": person_id, "error": str(exc)}},
                )
                similar_persons_data.append(
                    {
                        "person": person,
                        "similar_persons": [],
                    }
                )

        return similar_persons_data

    def _parse_ai_analysis(self, evidence_list: List[Dict]) -> Dict:
        """Extract and aggregate AI analysis from evidence records."""
        ai_analysis = {
            "scene": None,
            "persons": [],
            "objects": [],
            "transcription": None,
            "audio_events": [],
            "llm_reasoning": None,
        }

        for evidence in evidence_list:
            ai_data = evidence.get("ai_analysis")
            if not ai_data or not isinstance(ai_data, dict):
                continue

            # Extract scene data
            if "scene" in ai_data and not ai_analysis["scene"]:
                ai_analysis["scene"] = ai_data["scene"]

            # Extract person detections
            if "persons" in ai_data and isinstance(ai_data["persons"], list):
                ai_analysis["persons"].extend(ai_data["persons"])

            # Extract object detections
            if "objects" in ai_data and isinstance(ai_data["objects"], list):
                ai_analysis["objects"].extend(ai_data["objects"])

            # Extract transcription
            if "transcription" in ai_data and not ai_analysis["transcription"]:
                ai_analysis["transcription"] = ai_data["transcription"]

            # Extract audio events
            if "audio_events" in ai_data and isinstance(ai_data["audio_events"], list):
                ai_analysis["audio_events"].extend(ai_data["audio_events"])

            # Extract LLM reasoning
            if "llm_reasoning" in ai_data and not ai_analysis["llm_reasoning"]:
                ai_analysis["llm_reasoning"] = ai_data["llm_reasoning"]

        return ai_analysis

    def _generate_executive_summary(self, ticket_dict: Dict) -> Dict:
        """Generate executive summary from ticket data."""
        evidence_count = len(ticket_dict.get("evidence", []))
        person_count = len(ticket_dict.get("persons_of_interest", []))

        # Calculate response time
        response_time = None
        if ticket_dict.get("acknowledged_at"):
            created_at = datetime.fromisoformat(ticket_dict["created_at"].replace("Z", "+00:00"))
            acknowledged_at = datetime.fromisoformat(
                ticket_dict["acknowledged_at"].replace("Z", "+00:00")
            )
            response_time = (acknowledged_at - created_at).total_seconds()

        # Calculate resolution time
        resolution_time = None
        if ticket_dict.get("closed_at"):
            created_at = datetime.fromisoformat(ticket_dict["created_at"].replace("Z", "+00:00"))
            closed_at = datetime.fromisoformat(ticket_dict["closed_at"].replace("Z", "+00:00"))
            resolution_time = (closed_at - created_at).total_seconds()

        # Extract LLM reasoning summary (first 200 chars)
        llm_reasoning = None
        for evidence in ticket_dict.get("evidence", []):
            ai_data = evidence.get("ai_analysis")
            if ai_data and isinstance(ai_data, dict) and "llm_reasoning" in ai_data:
                llm_reasoning = ai_data["llm_reasoning"]
                if isinstance(llm_reasoning, dict):
                    reasoning_text = llm_reasoning.get("reasoning", "")
                else:
                    reasoning_text = str(llm_reasoning)
                if reasoning_text:
                    llm_reasoning = reasoning_text[:200] + "..." if len(reasoning_text) > 200 else reasoning_text
                break

        # Extract key factors (top 3)
        key_factors = []
        for evidence in ticket_dict.get("evidence", []):
            ai_data = evidence.get("ai_analysis")
            if ai_data and isinstance(ai_data, dict) and "llm_reasoning" in ai_data:
                llm_data = ai_data["llm_reasoning"]
                if isinstance(llm_data, dict) and "key_factors" in llm_data:
                    key_factors = llm_data["key_factors"][:3]
                    break

        return {
            "threat_level": ticket_dict.get("threat_level", "medium"),
            "priority": ticket_dict.get("priority", "medium"),
            "status": ticket_dict.get("status", "open"),
            "evidence_count": evidence_count,
            "person_count": person_count,
            "response_time_seconds": response_time,
            "resolution_time_seconds": resolution_time,
            "sla_breach": ticket_dict.get("sla_breach", False),
            "llm_reasoning_summary": llm_reasoning,
            "key_factors": key_factors,
        }

    def _generate_pdf_report(self, report_data: Dict) -> bytes:
        """Generate PDF report using ReportLab."""
        buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build flowables
        flowables = []

        # Executive Summary
        flowables.extend(self._build_executive_summary_section(report_data))

        # Incident Overview
        flowables.extend(self._build_incident_overview_section(report_data))

        # Timeline
        flowables.extend(self._build_timeline_section(report_data))

        # AI Analysis
        flowables.extend(self._build_ai_analysis_section(report_data))

        # Evidence Gallery
        flowables.extend(self._build_evidence_gallery_section(report_data))

        # Persons of Interest
        flowables.extend(self._build_persons_section(report_data))

        # Environmental Context
        flowables.extend(self._build_environmental_section(report_data))

        # Recommendations
        flowables.extend(self._build_recommendations_section(report_data))

        # Build PDF with watermark
        def add_watermark(canvas, doc):
            """Add watermark to every page with logo overlay and rotated text."""
            canvas.saveState()
            
            # Draw logo overlay if available
            logo_path = self.config.REPORT_LOGO_PATH
            if logo_path:
                logo_file = Path(logo_path)
                if not logo_file.is_absolute():
                    logo_file = self.storage_base_path / logo_path
                
                if logo_file.exists() and logo_file.is_file():
                    try:
                        # Draw semi-transparent logo near page center
                        canvas.setFillAlpha(0.15)  # Semi-transparent
                        logo_width = 2 * inch
                        logo_height = 2 * inch
                        logo_x = (self.page_size[0] - logo_width) / 2
                        logo_y = (self.page_size[1] - logo_height) / 2
                        canvas.drawImage(
                            str(logo_file),
                            logo_x,
                            logo_y,
                            width=logo_width,
                            height=logo_height,
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                        canvas.setFillAlpha(1.0)  # Reset alpha
                    except Exception as logo_exc:
                        logger.warning(
                            "Failed to draw logo watermark",
                            extra={"context": {"logo_path": str(logo_file), "error": str(logo_exc)}},
                        )
            
            # Draw rotated text watermark across page center
            canvas.saveState()
            canvas.setFont(self.font_name, 48)  # Large font for watermark
            canvas.setFillColor(colors.grey, alpha=0.15)  # Very transparent
            
            # Rotate and translate to center
            canvas.translate(self.page_size[0] / 2, self.page_size[1] / 2)
            canvas.rotate(45)  # Rotate 45 degrees
            
            # Draw watermark text
            watermark_text = self.config.REPORT_WATERMARK_TEXT
            text_width = canvas.stringWidth(watermark_text, self.font_name, 48)
            canvas.drawCentredString(0, 0, watermark_text)
            canvas.restoreState()
            
            # Footer text watermark
            canvas.setFont(self.font_name, 10)
            canvas.setFillColor(colors.grey, alpha=0.3)
            footer_text = f"{self.config.REPORT_WATERMARK_TEXT} - {report_data['ticket']['id'][:8]} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            canvas.drawCentredString(self.page_size[0] / 2, 30, footer_text)

            canvas.restoreState()

        doc.build(flowables, onFirstPage=add_watermark, onLaterPages=add_watermark)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _build_executive_summary_section(self, report_data: Dict) -> List[Flowable]:
        """Build executive summary section using ReportLab flowables."""
        flowables = []
        styles = getSampleStyleSheet()
        exec_summary = report_data["executive_summary"]

        # Title
        flowables.append(Paragraph("<b>Executive Summary</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # Threat Assessment
        flowables.append(Paragraph("<b>Threat Assessment:</b>", styles["Heading2"]))
        threat_items = [
            ListItem(Paragraph(f"<b>Threat Level:</b> {exec_summary.get('threat_level', 'N/A').upper()}", styles["Normal"])),
            ListItem(Paragraph(f"<b>Priority:</b> {exec_summary.get('priority', 'N/A').upper()}", styles["Normal"])),
            ListItem(Paragraph(f"<b>Status:</b> {exec_summary.get('status', 'N/A').upper()}", styles["Normal"])),
        ]
        flowables.append(ListFlowable(threat_items, bulletType='bullet'))
        flowables.append(Spacer(1, 0.15 * inch))

        # Key Statistics Table
        flowables.append(Paragraph("<b>Key Statistics:</b>", styles["Heading2"]))
        stats_data = [
            ["Evidence Count", str(exec_summary.get("evidence_count", 0))],
            ["Person Count", str(exec_summary.get("person_count", 0))],
        ]
        if exec_summary.get("response_time_seconds"):
            stats_data.append(["Response Time", f"{exec_summary['response_time_seconds'] / 60:.1f} minutes"])
        if exec_summary.get("resolution_time_seconds"):
            stats_data.append(["Resolution Time", f"{exec_summary['resolution_time_seconds'] / 60:.1f} minutes"])
        stats_data.append(["SLA Breach", "Yes" if exec_summary.get("sla_breach") else "No"])
        
        stats_table = Table(stats_data, colWidths=[2.5 * inch, 3 * inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        flowables.append(stats_table)
        flowables.append(Spacer(1, 0.15 * inch))

        # Summary text
        if exec_summary.get("llm_reasoning_summary"):
            flowables.append(Paragraph("<b>Summary:</b>", styles["Heading2"]))
            flowables.append(Paragraph(exec_summary["llm_reasoning_summary"], styles["Normal"]))
            flowables.append(Spacer(1, 0.15 * inch))

        # Key Factors
        if exec_summary.get("key_factors"):
            flowables.append(Paragraph("<b>Key Factors:</b>", styles["Heading2"]))
            factor_items = [ListItem(Paragraph(factor, styles["Normal"])) for factor in exec_summary["key_factors"]]
            flowables.append(ListFlowable(factor_items, bulletType='bullet'))
            flowables.append(Spacer(1, 0.15 * inch))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_incident_overview_section(self, report_data: Dict) -> List[Flowable]:
        """Build incident overview section using ReportLab flowables."""
        flowables = []
        styles = getSampleStyleSheet()
        ticket = report_data["ticket"]

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>Incident Overview</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # Build ticket details table
        ticket_data = [
            ["Ticket ID", ticket.get("id", "N/A")],
            ["Title", ticket.get("title", "N/A")],
            ["Status", ticket.get("status", "N/A").upper()],
            ["Priority", ticket.get("priority", "N/A").upper()],
            ["Threat Level", ticket.get("threat_level", "N/A").upper()],
            ["Created At", ticket.get("created_at", "N/A")],
        ]
        if ticket.get("acknowledged_at"):
            ticket_data.append(["Acknowledged At", ticket["acknowledged_at"]])
        if ticket.get("closed_at"):
            ticket_data.append(["Closed At", ticket["closed_at"]])
        if ticket.get("video"):
            ticket_data.append(["Video ID", ticket["video"].get("id", "N/A")])
        if ticket.get("assigned_user"):
            user = ticket["assigned_user"]
            ticket_data.append(["Assigned To", f"{user.get('username', 'N/A')} ({user.get('email', 'N/A')})"])
        ticket_data.append(["SLA Breach", "Yes" if ticket.get("sla_breach") else "No"])

        ticket_table = Table(ticket_data, colWidths=[2.5 * inch, 3 * inch])
        ticket_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        flowables.append(ticket_table)
        flowables.append(Spacer(1, 0.2 * inch))

        # Description
        if ticket.get("description"):
            flowables.append(Paragraph("<b>Description:</b>", styles["Heading2"]))
            flowables.append(Paragraph(ticket["description"], styles["Normal"]))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_timeline_section(self, report_data: Dict) -> List[Flowable]:
        """Build timeline section using ReportLab flowables."""
        flowables = []
        styles = getSampleStyleSheet()
        history = sorted(report_data.get("history", []), key=lambda x: x.get("occurred_at", ""))

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>Timeline</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # Build timeline entries
        for event in history:
            event_type = event.get("event", "unknown")
            occurred_at = event.get("occurred_at", "N/A")
            details = event.get("details")
            
            # Event icon/emoji mapping
            event_icons = {
                "created": "📝",
                "acknowledged": "✅",
                "escalated": "⚠️",
                "closed": "🔒",
            }
            icon = event_icons.get(event_type, "•")
            
            # Event header
            event_text = f"{icon} {occurred_at} - {event_type.upper()}"
            flowables.append(Paragraph(f"<b>{event_text}</b>", styles["Normal"]))
            
            # Event details
            if details:
                if isinstance(details, dict):
                    details_str = json.dumps(details, indent=2, default=str)
                else:
                    details_str = str(details)
                flowables.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{details_str}", styles["Normal"]))
            
            flowables.append(Spacer(1, 0.1 * inch))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_ai_analysis_section(self, report_data: Dict) -> List[Flowable]:
        """Build AI analysis section using ReportLab flowables."""
        flowables = []
        styles = getSampleStyleSheet()
        ai_analysis = report_data.get("ai_analysis", {})

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>AI Analysis Results</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # LLM Threat Assessment
        if ai_analysis.get("llm_reasoning"):
            flowables.append(Paragraph("<b>LLM Threat Assessment</b>", styles["Heading2"]))
            llm = ai_analysis["llm_reasoning"]
            if isinstance(llm, dict):
                if llm.get("reasoning"):
                    flowables.append(Paragraph(f"<b>Reasoning:</b> {llm['reasoning']}", styles["Normal"]))
                if llm.get("confidence"):
                    flowables.append(Paragraph(f"<b>Confidence:</b> {llm['confidence'] * 100:.2f}%", styles["Normal"]))
                if llm.get("key_factors"):
                    flowables.append(Paragraph("<b>Key Factors:</b>", styles["Normal"]))
                    factor_items = [ListItem(Paragraph(factor, styles["Normal"])) for factor in llm["key_factors"]]
                    flowables.append(ListFlowable(factor_items, bulletType='bullet'))
            flowables.append(Spacer(1, 0.15 * inch))

        # Scene Analysis
        if ai_analysis.get("scene"):
            flowables.append(Paragraph("<b>Scene Analysis</b>", styles["Heading2"]))
            scene = ai_analysis["scene"]
            scene_data = []
            if scene.get("scene_type"):
                scene_data.append(["Scene Type", scene["scene_type"]])
            if scene.get("lighting"):
                scene_data.append(["Lighting", scene["lighting"]])
            if scene.get("weather"):
                scene_data.append(["Weather", scene["weather"]])
            if scene.get("crowd_density"):
                scene_data.append(["Crowd Density", scene["crowd_density"]])
            if scene.get("description"):
                scene_data.append(["Description", scene["description"]])
            
            if scene_data:
                scene_table = Table(scene_data, colWidths=[2.5 * inch, 3 * inch])
                scene_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                flowables.append(scene_table)
            flowables.append(Spacer(1, 0.15 * inch))

        # Person Detections
        if ai_analysis.get("persons"):
            flowables.append(Paragraph("<b>Person Detections</b>", styles["Heading2"]))
            persons = ai_analysis["persons"][:10]
            person_data = [["Age", "Gender", "Ethnicity", "Confidence"]]
            for person in persons:
                person_data.append([
                    person.get("age_estimate", "N/A") if isinstance(person, dict) else getattr(person, "age_estimate", "N/A"),
                    person.get("gender", "N/A") if isinstance(person, dict) else getattr(person, "gender", "N/A"),
                    person.get("ethnicity", "N/A") if isinstance(person, dict) else getattr(person, "ethnicity", "N/A"),
                    f"{person.get('confidence', 0) * 100:.2f}%" if isinstance(person, dict) and person.get("confidence") else "N/A",
                ])
            person_table = Table(person_data, colWidths=[1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
            person_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            flowables.append(person_table)
            flowables.append(Spacer(1, 0.15 * inch))

        # Object Detections
        if ai_analysis.get("objects"):
            flowables.append(Paragraph("<b>Object Detections</b>", styles["Heading2"]))
            objects = ai_analysis["objects"][:20]
            obj_data = [["Object", "Confidence", "Threat Level"]]
            for obj in objects:
                obj_data.append([
                    obj.get("class_name", "Unknown") if isinstance(obj, dict) else getattr(obj, "class_name", "Unknown"),
                    f"{obj.get('confidence', 0) * 100:.2f}%" if isinstance(obj, dict) and obj.get("confidence") else "N/A",
                    obj.get("threat_level", "N/A").upper() if isinstance(obj, dict) and obj.get("threat_level") else "N/A",
                ])
            obj_table = Table(obj_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
            obj_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            flowables.append(obj_table)
            flowables.append(Spacer(1, 0.15 * inch))

        # Audio Transcription
        if ai_analysis.get("transcription"):
            flowables.append(Paragraph("<b>Audio Transcription</b>", styles["Heading2"]))
            transcription = ai_analysis["transcription"]
            if isinstance(transcription, dict):
                flowables.append(Paragraph(transcription.get("text", str(transcription)), styles["Normal"]))
                if transcription.get("confidence"):
                    flowables.append(Paragraph(f"<b>Confidence:</b> {transcription['confidence'] * 100:.2f}%", styles["Normal"]))
            else:
                flowables.append(Paragraph(str(transcription), styles["Normal"]))
            flowables.append(Spacer(1, 0.15 * inch))

        # Audio Events
        if ai_analysis.get("audio_events"):
            flowables.append(Paragraph("<b>Audio Events</b>", styles["Heading2"]))
            events = ai_analysis["audio_events"][:10]
            event_items = []
            for event in events:
                event_type = event.get("event_type", "Unknown") if isinstance(event, dict) else getattr(event, "event_type", "Unknown")
                confidence = event.get("confidence", 0) if isinstance(event, dict) else getattr(event, "confidence", 0)
                event_text = f"{event_type} ({confidence * 100:.2f}%)" if confidence else event_type
                event_items.append(ListItem(Paragraph(event_text, styles["Normal"])))
            flowables.append(ListFlowable(event_items, bulletType='bullet'))
            flowables.append(Spacer(1, 0.15 * inch))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_evidence_gallery_section(self, report_data: Dict) -> List[Flowable]:
        """Build evidence gallery section with embedded images."""
        flowables = []
        styles = getSampleStyleSheet()
        evidence_list = report_data.get("evidence", [])

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>Evidence Gallery</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # Frame Evidence with images
        frame_evidence = [e for e in evidence_list if e.get("type") == "frame"]
        if frame_evidence:
            flowables.append(Paragraph("<b>Frame Evidence</b>", styles["Heading2"]))
            for frame in frame_evidence:
                # Frame metadata
                frame_num = frame.get("frame_number", "N/A")
                timestamp = frame.get("timestamp", "N/A")
                description = frame.get("description", "")
                confidence = frame.get("confidence_score")
                
                frame_info = f"<b>Frame #{frame_num}</b><br/>"
                frame_info += f"<b>Timestamp:</b> {timestamp}<br/>"
                if description:
                    frame_info += f"<b>Description:</b> {description}<br/>"
                if confidence is not None:
                    frame_info += f"<b>Confidence:</b> {confidence * 100:.2f}%<br/>"
                
                flowables.append(Paragraph(frame_info, styles["Normal"]))
                
                # Embed image if filepath exists
                filepath = frame.get("filepath")
                if filepath:
                    image_path = self.storage_base_path / filepath if not Path(filepath).is_absolute() else Path(filepath)
                    if image_path.exists() and image_path.is_file():
                        try:
                            # Calculate image dimensions to fit page width (with margins)
                            page_width = self.page_size[0] - 144  # 72*2 for margins
                            img = RLImage(str(image_path), width=page_width, height=None, kind='proportional')
                            flowables.append(img)
                            flowables.append(Spacer(1, 0.1 * inch))
                        except Exception as img_exc:
                            logger.warning(
                                "Failed to embed evidence image",
                                extra={"context": {"filepath": str(image_path), "error": str(img_exc)}},
                            )
                            flowables.append(Paragraph(f"<i>Image unavailable: {str(img_exc)}</i>", styles["Normal"]))
                    else:
                        flowables.append(Paragraph(f"<i>Image file not found: {filepath}</i>", styles["Normal"]))
                
                flowables.append(Spacer(1, 0.2 * inch))

        # Audio Evidence
        audio_evidence = [e for e in evidence_list if e.get("type") == "audio"]
        if audio_evidence:
            flowables.append(Paragraph("<b>Audio Evidence</b>", styles["Heading2"]))
            for audio in audio_evidence:
                audio_info = f"<b>Audio File</b><br/>"
                audio_info += f"<b>Timestamp:</b> {audio.get('timestamp', 'N/A')}<br/>"
                if audio.get("description"):
                    audio_info += f"<b>Description:</b> {audio['description']}<br/>"
                flowables.append(Paragraph(audio_info, styles["Normal"]))
                flowables.append(Spacer(1, 0.1 * inch))

        # Video Evidence
        video_evidence = [e for e in evidence_list if e.get("type") == "video"]
        if video_evidence:
            flowables.append(Paragraph("<b>Video Evidence</b>", styles["Heading2"]))
            for video in video_evidence:
                video_info = f"<b>Video Clip</b><br/>"
                video_info += f"<b>Timestamp:</b> {video.get('timestamp', 'N/A')}<br/>"
                if video.get("description"):
                    video_info += f"<b>Description:</b> {video['description']}<br/>"
                flowables.append(Paragraph(video_info, styles["Normal"]))
                flowables.append(Spacer(1, 0.1 * inch))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_persons_section(self, report_data: Dict) -> List[Flowable]:
        """Build persons of interest section with embedded thumbnails."""
        flowables = []
        styles = getSampleStyleSheet()
        persons_list = report_data.get("persons", [])
        similar_persons_data = report_data.get("similar_persons", [])

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>Persons of Interest</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        for idx, person in enumerate(persons_list, 1):
            flowables.append(Paragraph(f"<b>Person {idx}</b>", styles["Heading2"]))
            
            # Person details table
            person_data = [
                ["Tracking ID", person.get("person_tracking_id", "N/A")],
                ["Age Estimate", person.get("age_estimate", "N/A")],
                ["Gender", person.get("gender", "N/A")],
                ["Ethnicity", person.get("ethnicity", "N/A")],
                ["Clothing Description", person.get("clothing_description", "N/A")],
            ]
            
            person_table = Table(person_data, colWidths=[2.5 * inch, 3 * inch])
            person_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            flowables.append(person_table)
            flowables.append(Spacer(1, 0.15 * inch))
            
            # Embed person thumbnail if available
            thumbnail_path = person.get("thumbnail_path")
            if thumbnail_path:
                img_path = self.storage_base_path / thumbnail_path if not Path(thumbnail_path).is_absolute() else Path(thumbnail_path)
                if img_path.exists() and img_path.is_file():
                    try:
                        # Scale thumbnail to reasonable size (max 2 inches width)
                        max_width = 2 * inch
                        img = RLImage(str(img_path), width=max_width, height=None, kind='proportional')
                        flowables.append(img)
                        flowables.append(Spacer(1, 0.1 * inch))
                    except Exception as img_exc:
                        logger.warning(
                            "Failed to embed person thumbnail",
                            extra={"context": {"filepath": str(img_path), "error": str(img_exc)}},
                        )
                        flowables.append(Paragraph(f"<i>Thumbnail unavailable: {str(img_exc)}</i>", styles["Normal"]))
                else:
                    flowables.append(Paragraph(f"<i>Thumbnail file not found: {thumbnail_path}</i>", styles["Normal"]))
            
            # Similar persons
            for similar_group in similar_persons_data:
                if similar_group.get("person", {}).get("id") == person.get("id") and similar_group.get("similar_persons"):
                    flowables.append(Paragraph("<b>Similar Persons</b>", styles["Heading3"]))
                    similar_persons = similar_group["similar_persons"][:5]
                    
                    # Similar persons table
                    similar_data = [["Tracking ID", "Similarity Score", "Age", "Gender"]]
                    for similar in similar_persons:
                        similar_person = similar.get("person", {}) if isinstance(similar, dict) else similar.person
                        similar_data.append([
                            similar_person.get("person_tracking_id", "N/A") if isinstance(similar_person, dict) else getattr(similar_person, "person_tracking_id", "N/A"),
                            f"{similar.get('score', 0) * 100:.2f}%" if isinstance(similar, dict) and similar.get("score") else "N/A",
                            similar_person.get("age_estimate", "N/A") if isinstance(similar_person, dict) else getattr(similar_person, "age_estimate", "N/A"),
                            similar_person.get("gender", "N/A") if isinstance(similar_person, dict) else getattr(similar_person, "gender", "N/A"),
                        ])
                    
                    similar_table = Table(similar_data, colWidths=[1.5 * inch, 1.5 * inch, 1 * inch, 1 * inch])
                    similar_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    flowables.append(similar_table)
                    
                    # Embed similar person thumbnails
                    for similar in similar_persons:
                        similar_person = similar.get("person", {}) if isinstance(similar, dict) else similar.person
                        similar_thumbnail = similar_person.get("thumbnail_path") if isinstance(similar_person, dict) else getattr(similar_person, "thumbnail_path", None)
                        if similar_thumbnail:
                            similar_img_path = self.storage_base_path / similar_thumbnail if not Path(similar_thumbnail).is_absolute() else Path(similar_thumbnail)
                            if similar_img_path.exists() and similar_img_path.is_file():
                                try:
                                    max_width = 1.5 * inch
                                    img = RLImage(str(similar_img_path), width=max_width, height=None, kind='proportional')
                                    flowables.append(img)
                                    flowables.append(Spacer(1, 0.05 * inch))
                                except Exception as img_exc:
                                    logger.warning(
                                        "Failed to embed similar person thumbnail",
                                        extra={"context": {"filepath": str(similar_img_path), "error": str(img_exc)}},
                                    )
            
            flowables.append(Spacer(1, 0.3 * inch))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_environmental_section(self, report_data: Dict) -> List[Flowable]:
        """Build environmental context section using ReportLab flowables."""
        flowables = []
        styles = getSampleStyleSheet()
        ai_analysis = report_data.get("ai_analysis", {})
        ticket = report_data.get("ticket", {})

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>Environmental Context</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # Scene Details
        if ai_analysis.get("scene"):
            flowables.append(Paragraph("<b>Scene Details</b>", styles["Heading2"]))
            scene = ai_analysis["scene"]
            scene_data = []
            if scene.get("scene_type"):
                scene_data.append(["Scene Type", scene["scene_type"]])
            if scene.get("lighting"):
                scene_data.append(["Lighting", scene["lighting"]])
            if scene.get("weather"):
                scene_data.append(["Weather", scene["weather"]])
            if scene.get("time_of_day"):
                scene_data.append(["Time of Day", scene["time_of_day"]])
            if scene.get("crowd_density"):
                scene_data.append(["Crowd Density", scene["crowd_density"]])
            if scene.get("visibility"):
                scene_data.append(["Visibility", scene["visibility"]])
            
            if scene_data:
                scene_table = Table(scene_data, colWidths=[2.5 * inch, 3 * inch])
                scene_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                flowables.append(scene_table)
            
            if scene.get("description"):
                flowables.append(Spacer(1, 0.15 * inch))
                flowables.append(Paragraph("<b>Detailed Scene Description:</b>", styles["Heading3"]))
                flowables.append(Paragraph(scene["description"], styles["Normal"]))
            flowables.append(Spacer(1, 0.15 * inch))

        # Location Information
        if ticket.get("video"):
            flowables.append(Paragraph("<b>Location Information</b>", styles["Heading2"]))
            video = ticket["video"]
            location_data = [
                ["Video ID", video.get("id", "N/A")],
                ["Video Filename", video.get("filename", "N/A")],
            ]
            location_table = Table(location_data, colWidths=[2.5 * inch, 3 * inch])
            location_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            flowables.append(location_table)

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _build_recommendations_section(self, report_data: Dict) -> List[Flowable]:
        """Build recommendations section using ReportLab flowables."""
        flowables = []
        styles = getSampleStyleSheet()
        ticket = report_data.get("ticket", {})
        ai_analysis = report_data.get("ai_analysis", {})

        flowables.append(PageBreak())
        flowables.append(Paragraph("<b>Recommendations</b>", styles["Heading1"]))
        flowables.append(Spacer(1, 0.2 * inch))

        # Recommended Action
        if ai_analysis.get("llm_reasoning") and isinstance(ai_analysis["llm_reasoning"], dict):
            recommended_action = ai_analysis["llm_reasoning"].get("recommended_action")
            if recommended_action:
                flowables.append(Paragraph("<b>Recommended Action:</b>", styles["Heading2"]))
                flowables.append(Paragraph(recommended_action, styles["Normal"]))
                flowables.append(Spacer(1, 0.15 * inch))

        # Next Steps based on threat level
        flowables.append(Paragraph("<b>Next Steps</b>", styles["Heading2"]))
        threat_level = ticket.get("threat_level", "low").lower()
        next_steps = []
        if threat_level == "critical":
            next_steps = [
                "Immediate security response required",
                "Notify emergency services if necessary",
                "Escalate to senior management",
                "Document all actions taken",
            ]
        elif threat_level == "high":
            next_steps = [
                "Priority investigation required",
                "Review all evidence thoroughly",
                "Coordinate with security team",
                "Update incident log",
            ]
        elif threat_level == "medium":
            next_steps = [
                "Standard investigation procedure",
                "Review evidence and timeline",
                "Monitor for similar incidents",
                "Follow-up as needed",
            ]
        else:
            next_steps = [
                "Routine review",
                "Document findings",
                "Monitor for escalation",
            ]
        
        step_items = [ListItem(Paragraph(step, styles["Normal"])) for step in next_steps]
        flowables.append(ListFlowable(step_items, bulletType='bullet'))
        flowables.append(Spacer(1, 0.15 * inch))

        # Follow-up Actions
        flowables.append(Paragraph("<b>Follow-up Actions</b>", styles["Heading2"]))
        followup_steps = [
            "Review similar incidents in the system",
            "Update security protocols if needed",
            "Conduct training review if patterns identified",
            "Schedule follow-up review meeting",
        ]
        followup_items = [ListItem(Paragraph(step, styles["Normal"])) for step in followup_steps]
        flowables.append(ListFlowable(followup_items, bulletType='bullet'))
        flowables.append(Spacer(1, 0.15 * inch))

        # Escalation Contacts
        flowables.append(Paragraph("<b>Escalation Contacts</b>", styles["Heading2"]))
        contacts = [
            "Security Team: security@vigilanteye.local",
            "Emergency: emergency@vigilanteye.local",
            "Management: management@vigilanteye.local",
        ]
        contact_items = [ListItem(Paragraph(contact, styles["Normal"])) for contact in contacts]
        flowables.append(ListFlowable(contact_items, bulletType='bullet'))

        flowables.append(Spacer(1, 0.3 * inch))
        return flowables

    def _generate_json_report(self, report_data: Dict) -> str:
        """Generate JSON report."""
        return json.dumps(report_data, indent=2, default=str)

    def invalidate_cache(self, ticket_id: str) -> None:
        """Invalidate cached reports for a ticket."""
        if not self.redis_client:
            return

        try:
            cache_keys = [
                f"report:{ticket_id}:pdf",
                f"report:{ticket_id}:json",
            ]
            for key in cache_keys:
                self.redis_client.delete(key)
            logger.info(
                "Report cache invalidated",
                extra={"context": {"ticket_id": ticket_id}},
            )
        except Exception as exc:
            logger.warning(
                "Failed to invalidate report cache",
                extra={"context": {"ticket_id": ticket_id, "error": str(exc)}},
            )

