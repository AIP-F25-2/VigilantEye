"""Ticket repository."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ticket import (
    Ticket,
    TicketActivity,
    TicketEvidence,
    TicketPriority,
    TicketStatus,
)


class TicketRepository:
    """Repository for Ticket model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        threat_assessment_id: int,
        ticket_number: str,
        title: str,
        description: str,
        priority: TicketPriority,
        video_id: int,
        frame_timestamp_ms: int,
        processing_id: str,
        auto_close_at: datetime,
    ) -> Ticket:
        """Create a new ticket."""
        ticket = Ticket(
            threat_assessment_id=threat_assessment_id,
            ticket_number=ticket_number,
            title=title,
            description=description,
            priority=priority,
            status=TicketStatus.OPEN,
            video_id=video_id,
            frame_timestamp_ms=frame_timestamp_ms,
            processing_id=processing_id,
            auto_close_at=auto_close_at,
        )
        
        self.session.add(ticket)
        await self.session.flush()
        await self.session.refresh(ticket)
        return ticket

    async def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Get ticket by ID."""
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticket_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number."""
        result = await self.session.execute(
            select(Ticket).where(Ticket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Ticket], int]:
        """Get all tickets with filters."""
        query = select(Ticket).where(Ticket.deleted_at.is_(None))  # Exclude soft-deleted tickets
        
        if status:
            query = query.where(Ticket.status == status)
        
        if priority:
            query = query.where(Ticket.priority == priority)
        
        # Count total
        count_query = select(func.count()).select_from(Ticket).where(Ticket.deleted_at.is_(None))
        if status:
            count_query = count_query.where(Ticket.status == status)
        if priority:
            count_query = count_query.where(Ticket.priority == priority)
        
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        
        # Get tickets
        query = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        tickets = list(result.scalars().all())
        
        return tickets, total

    async def get_open_tickets(self) -> List[Ticket]:
        """Get all open tickets."""
        result = await self.session.execute(
            select(Ticket).where(
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.ESCALATED])
            )
        )
        return list(result.scalars().all())

    async def get_overdue_tickets(self) -> List[Ticket]:
        """Get tickets that are overdue for auto-close."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Ticket).where(
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.ESCALATED]),
                Ticket.auto_close_at <= now
            )
        )
        return list(result.scalars().all())

    async def get_tickets_for_escalation(self, timeout_datetime: datetime) -> List[Ticket]:
        """Get tickets that need escalation."""
        result = await self.session.execute(
            select(Ticket).where(
                Ticket.status == TicketStatus.OPEN,
                Ticket.created_at <= timeout_datetime
            )
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        ticket_id: int,
        new_status: TicketStatus,
        user_id: Optional[int] = None,
    ) -> Optional[Ticket]:
        """Update ticket status."""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return None
        
        ticket.status = new_status
        
        if new_status == TicketStatus.ACKNOWLEDGED:
            ticket.acknowledged_at = datetime.utcnow()
            ticket.acknowledged_by_user_id = user_id
            
            if ticket.created_at:
                delta = datetime.utcnow() - ticket.created_at
                ticket.acknowledgment_time_seconds = int(delta.total_seconds())
        
        elif new_status == TicketStatus.ESCALATED:
            ticket.escalated_at = datetime.utcnow()
        
        elif new_status in [TicketStatus.CLOSED, TicketStatus.AUTO_CLOSED]:
            ticket.closed_at = datetime.utcnow()
            ticket.closed_by_user_id = user_id
            
            if ticket.created_at:
                delta = datetime.utcnow() - ticket.created_at
                ticket.resolution_time_seconds = int(delta.total_seconds())
        
        await self.session.flush()
        await self.session.refresh(ticket)
        return ticket

    async def add_evidence(
        self,
        ticket_id: int,
        storage_file_id: int,
        evidence_type: str,
        file_path: str,
        file_name: str,
        matched_face_id: Optional[str] = None,
        match_confidence: Optional[float] = None,
        source_video_id: Optional[int] = None,
        frame_timestamp_ms: Optional[int] = None,
        description: Optional[str] = None,
    ) -> TicketEvidence:
        """Add evidence to ticket."""
        evidence = TicketEvidence(
            ticket_id=ticket_id,
            storage_file_id=storage_file_id,
            evidence_type=evidence_type,
            file_path=file_path,
            file_name=file_name,
            matched_face_id=matched_face_id,
            match_confidence=match_confidence,
            source_video_id=source_video_id,
            frame_timestamp_ms=frame_timestamp_ms,
            description=description,
        )
        
        self.session.add(evidence)
        await self.session.flush()
        return evidence

    async def get_ticket_evidence(self, ticket_id: int) -> List[TicketEvidence]:
        """Get all evidence for a ticket."""
        result = await self.session.execute(
            select(TicketEvidence)
            .where(TicketEvidence.ticket_id == ticket_id)
            .order_by(TicketEvidence.created_at)
        )
        return list(result.scalars().all())

    async def log_activity(
        self,
        ticket_id: int,
        action: str,
        user_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> TicketActivity:
        """Log ticket activity."""
        activity = TicketActivity(
            ticket_id=ticket_id,
            user_id=user_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            comment=comment,
            metadata=metadata,
        )
        
        self.session.add(activity)
        await self.session.flush()
        return activity

    async def get_ticket_activities(self, ticket_id: int) -> List[TicketActivity]:
        """Get all activities for a ticket."""
        result = await self.session.execute(
            select(TicketActivity)
            .where(TicketActivity.ticket_id == ticket_id)
            .order_by(TicketActivity.created_at)
        )
        return list(result.scalars().all())

    async def search_tickets(
        self,
        query: str,
        status: Optional[TicketStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Ticket], int]:
        """Search tickets by query."""
        search_query = select(Ticket).where(
            or_(
                Ticket.ticket_number.ilike(f"%{query}%"),
                Ticket.title.ilike(f"%{query}%"),
                Ticket.description.ilike(f"%{query}%"),
            )
        )
        
        if status:
            search_query = search_query.where(Ticket.status == status)
        
        # Count
        count_query = select(func.count()).select_from(Ticket).where(
            or_(
                Ticket.ticket_number.ilike(f"%{query}%"),
                Ticket.title.ilike(f"%{query}%"),
                Ticket.description.ilike(f"%{query}%"),
            )
        )
        
        if status:
            count_query = count_query.where(Ticket.status == status)
        
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        
        # Get results
        search_query = search_query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(search_query)
        tickets = list(result.scalars().all())
        
        return tickets, total

    async def delete_evidence(self, evidence_id: int) -> bool:
        """Delete evidence by ID."""
        result = await self.session.execute(
            select(TicketEvidence).where(TicketEvidence.id == evidence_id)
        )
        evidence = result.scalar_one_or_none()
        
        if evidence:
            await self.session.delete(evidence)
            await self.session.flush()
            return True
        
        return False

    async def get_ticket_stats(self) -> dict:
        """Get ticket statistics."""
        # Count by status
        result = await self.session.execute(
            select(
                Ticket.status,
                func.count(Ticket.id).label('count')
            ).group_by(Ticket.status)
        )
        
        status_counts = {row.status.value: row.count for row in result}
        
        # Average resolution time
        result = await self.session.execute(
            select(func.avg(Ticket.resolution_time_seconds))
            .where(Ticket.resolution_time_seconds.isnot(None))
        )
        avg_resolution = result.scalar_one_or_none() or 0
        
        # Average acknowledgment time
        result = await self.session.execute(
            select(func.avg(Ticket.acknowledgment_time_seconds))
            .where(Ticket.acknowledgment_time_seconds.isnot(None))
        )
        avg_ack = result.scalar_one_or_none() or 0
        
        return {
            'status_counts': status_counts,
            'avg_resolution_time_seconds': float(avg_resolution),
            'avg_acknowledgment_time_seconds': float(avg_ack),
        }
