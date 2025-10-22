"""Ticket DTOs."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.dto.base import BaseDTO


class TicketResponse(BaseDTO):
    """Ticket response model."""
    
    id: int
    ticket_number: str
    title: str
    description: str
    status: str
    priority: str
    acknowledged_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    auto_close_at: datetime
    acknowledged_by_user_id: Optional[int] = None
    closed_by_user_id: Optional[int] = None
    video_id: int
    frame_timestamp_ms: int
    processing_id: str
    evidence_folder_path: Optional[str] = None
    evidence_report_path: Optional[str] = None
    total_evidence_files: int = 0
    telegram_message_id: Optional[str] = None
    telegram_channel: Optional[str] = None
    escalation_message_id: Optional[str] = None
    acknowledgment_time_seconds: Optional[int] = None
    resolution_time_seconds: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseDTO):
    """Ticket list response model."""
    
    tickets: List[TicketResponse]
    total: int
    skip: int
    limit: int


class TicketCreateRequest(BaseDTO):
    """Ticket creation request model."""
    
    threat_assessment_id: int
    title: str
    description: str
    priority: str = "MEDIUM"
    video_id: int
    frame_timestamp_ms: int
    processing_id: str


class TicketUpdateRequest(BaseDTO):
    """Ticket update request model."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class TicketAcknowledgeRequest(BaseDTO):
    """Ticket acknowledge request model."""
    
    notes: Optional[str] = None


class TicketCloseRequest(BaseDTO):
    """Ticket close request model."""
    
    notes: Optional[str] = None


class TicketNoteRequest(BaseDTO):
    """Ticket note request model."""
    
    note: str = Field(..., min_length=1, max_length=1000)


class TicketEvidenceResponse(BaseDTO):
    """Ticket evidence response model."""
    
    id: int
    ticket_id: int
    storage_file_id: int
    evidence_type: str
    file_path: str
    file_name: str
    matched_face_id: Optional[str] = None
    match_confidence: Optional[float] = None
    source_video_id: Optional[int] = None
    frame_timestamp_ms: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime


class TicketStatsResponse(BaseDTO):
    """Ticket statistics response model."""
    
    total_tickets: int
    open_tickets: int
    acknowledged_tickets: int
    escalated_tickets: int
    closed_tickets: int
    auto_closed_tickets: int
    avg_acknowledgment_time_minutes: Optional[float] = None
    avg_resolution_time_minutes: Optional[float] = None
    escalation_rate_percent: Optional[float] = None
