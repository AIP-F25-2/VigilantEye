"""Ticket service for business logic."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import shutil
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ticket import TicketStatus, TicketPriority, TicketEvidence
from src.repositories.ticket import TicketRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TicketService:
    """Service for ticket business logic."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.repository = TicketRepository(session)

    async def acknowledge_ticket(
        self,
        ticket_id: int,
        user_id: int,
        notes: Optional[str] = None
    ) -> 'Ticket':
        """Acknowledge a ticket."""
        ticket = await self.repository.get_by_id(ticket_id)
        
        if not ticket:
            raise ValueError("Ticket not found")
        
        if ticket.status not in [TicketStatus.OPEN, TicketStatus.ESCALATED]:
            raise ValueError(f"Cannot acknowledge ticket with status: {ticket.status}")
        
        # Calculate acknowledgment time
        acknowledgment_time = None
        if ticket.status == TicketStatus.OPEN:
            acknowledgment_time = int((datetime.utcnow() - ticket.created_at).total_seconds())
        
        # Update ticket
        ticket = await self.repository.update_status(
            ticket_id=ticket_id,
            new_status=TicketStatus.ACKNOWLEDGED,
            user_id=user_id
        )
        
        # Update acknowledgment time
        if acknowledgment_time:
            ticket.acknowledged_at = datetime.utcnow()
            ticket.acknowledgment_time_seconds = acknowledgment_time
            await self.session.commit()
        
        # Log activity
        await self.repository.log_activity(
            ticket_id=ticket_id,
            action="ACKNOWLEDGED",
            user_id=user_id,
            old_status=ticket.status.value,
            new_status=TicketStatus.ACKNOWLEDGED.value,
            comment=notes
        )
        
        logger.info(f"Ticket {ticket_id} acknowledged by user {user_id}")
        return ticket

    async def close_ticket(
        self,
        ticket_id: int,
        user_id: int,
        notes: Optional[str] = None
    ) -> 'Ticket':
        """Close a ticket."""
        ticket = await self.repository.get_by_id(ticket_id)
        
        if not ticket:
            raise ValueError("Ticket not found")
        
        if ticket.status == TicketStatus.CLOSED:
            raise ValueError("Ticket is already closed")
        
        # Calculate resolution time
        resolution_time = None
        if ticket.acknowledged_at:
            resolution_time = int((datetime.utcnow() - ticket.acknowledged_at).total_seconds())
        else:
            resolution_time = int((datetime.utcnow() - ticket.created_at).total_seconds())
        
        # Update ticket
        ticket = await self.repository.update_status(
            ticket_id=ticket_id,
            new_status=TicketStatus.CLOSED,
            user_id=user_id
        )
        
        # Update resolution time
        ticket.closed_at = datetime.utcnow()
        ticket.resolution_time_seconds = resolution_time
        await self.session.commit()
        
        # Log activity
        await self.repository.log_activity(
            ticket_id=ticket_id,
            action="CLOSED",
            user_id=user_id,
            old_status=ticket.status.value,
            new_status=TicketStatus.CLOSED.value,
            comment=notes
        )
        
        logger.info(f"Ticket {ticket_id} closed by user {user_id}")
        return ticket

    async def add_note(
        self,
        ticket_id: int,
        user_id: int,
        note: str
    ) -> 'Ticket':
        """Add a note to a ticket."""
        ticket = await self.repository.get_by_id(ticket_id)
        
        if not ticket:
            raise ValueError("Ticket not found")
        
        # Update notes
        if ticket.notes:
            ticket.notes += f"\n\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {note}"
        else:
            ticket.notes = f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {note}"
        
        await self.session.commit()
        
        # Log activity
        await self.repository.log_activity(
            ticket_id=ticket_id,
            action="NOTE_ADDED",
            user_id=user_id,
            comment=note
        )
        
        logger.info(f"Note added to ticket {ticket_id} by user {user_id}")
        return ticket

    async def delete_evidence(self, evidence_id: int) -> None:
        """Delete evidence file."""
        # This would need to be implemented in the repository
        # For now, just log the action
        logger.info(f"Evidence {evidence_id} deletion requested")

    async def get_statistics(self) -> Dict:
        """Get ticket statistics."""
        from sqlalchemy import func, select
        
        # Get counts by status
        status_counts = await self.session.execute(
            select(TicketStatus, func.count())
            .select_from(self.repository.model)
            .group_by(TicketStatus)
        )
        
        stats = {
            'total_tickets': 0,
            'open_tickets': 0,
            'acknowledged_tickets': 0,
            'escalated_tickets': 0,
            'closed_tickets': 0,
            'auto_closed_tickets': 0,
            'avg_acknowledgment_time_minutes': None,
            'avg_resolution_time_minutes': None,
            'escalation_rate_percent': None,
        }
        
        for status, count in status_counts:
            stats['total_tickets'] += count
            if status == TicketStatus.OPEN:
                stats['open_tickets'] = count
            elif status == TicketStatus.ACKNOWLEDGED:
                stats['acknowledged_tickets'] = count
            elif status == TicketStatus.ESCALATED:
                stats['escalated_tickets'] = count
            elif status == TicketStatus.CLOSED:
                stats['closed_tickets'] = count
            elif status == TicketStatus.AUTO_CLOSED:
                stats['auto_closed_tickets'] = count
        
        # Calculate averages
        avg_ack_result = await self.session.execute(
            select(func.avg(self.repository.model.acknowledgment_time_seconds))
            .where(self.repository.model.acknowledgment_time_seconds.isnot(None))
        )
        avg_ack = avg_ack_result.scalar()
        if avg_ack:
            stats['avg_acknowledgment_time_minutes'] = round(avg_ack / 60, 2)
        
        avg_res_result = await self.session.execute(
            select(func.avg(self.repository.model.resolution_time_seconds))
            .where(self.repository.model.resolution_time_seconds.isnot(None))
        )
        avg_res = avg_res_result.scalar()
        if avg_res:
            stats['avg_resolution_time_minutes'] = round(avg_res / 60, 2)
        
        # Calculate escalation rate
        if stats['total_tickets'] > 0:
            escalated_total = stats['escalated_tickets'] + stats['closed_tickets'] + stats['auto_closed_tickets']
            if escalated_total > 0:
                stats['escalation_rate_percent'] = round(
                    (stats['escalated_tickets'] / escalated_total) * 100, 2
                )
        
        return stats

    async def soft_delete_ticket(self, ticket_id: int) -> bool:
        """Soft delete a ticket by setting deleted_at timestamp."""
        try:
            ticket = await self.repository.get_by_id(ticket_id)
            
            if not ticket:
                raise ValueError("Ticket not found")
            
            # Set deleted_at timestamp (soft delete)
            ticket.deleted_at = datetime.utcnow()
            await self.session.commit()
            
            # Log activity
            await self.repository.log_activity(
                ticket_id=ticket_id,
                action="SOFT_DELETED",
                comment="Ticket soft deleted by admin"
            )
            
            logger.info(f"Ticket {ticket_id} soft deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to soft delete ticket {ticket_id}: {e}")
            raise

    async def delete_evidence(self, evidence_id: int) -> bool:
        """Delete evidence file."""
        try:
            # Get evidence record
            result = await self.session.execute(
                select(TicketEvidence).where(TicketEvidence.id == evidence_id)
            )
            evidence = result.scalar_one_or_none()
            
            if not evidence:
                raise ValueError("Evidence not found")
            
            # Delete physical file if it exists
            file_path = Path(evidence.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Delete database record
            await self.session.delete(evidence)
            await self.session.commit()
            
            logger.info(f"Evidence {evidence_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete evidence {evidence_id}: {e}")
            raise

    async def create_evidence_zip(self, ticket_id: int) -> bytes:
        """Create ZIP archive of all evidence files for a ticket."""
        try:
            # Get all evidence for ticket
            result = await self.session.execute(
                select(TicketEvidence).where(TicketEvidence.ticket_id == ticket_id)
            )
            evidence_list = result.scalars().all()
            
            if not evidence_list:
                raise ValueError("No evidence found for ticket")
            
            # Create ZIP in memory
            zip_buffer = zipfile.ZipFile('temp_evidence.zip', 'w', zipfile.ZIP_DEFLATED)
            
            try:
                for evidence in evidence_list:
                    file_path = Path(evidence.file_path)
                    if file_path.exists():
                        # Add file to ZIP with original filename
                        zip_buffer.write(file_path, evidence.file_name)
                    else:
                        logger.warning(f"Evidence file not found: {file_path}")
                
                # Add metadata file
                metadata = {
                    'ticket_id': ticket_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'evidence_count': len(evidence_list),
                    'files': [
                        {
                            'file_name': e.file_name,
                            'evidence_type': e.evidence_type,
                            'created_at': e.created_at.isoformat(),
                            'description': e.description
                        }
                        for e in evidence_list
                    ]
                }
                
                zip_buffer.writestr('metadata.json', json.dumps(metadata, indent=2))
                
            finally:
                zip_buffer.close()
            
            # Read ZIP data
            with open('temp_evidence.zip', 'rb') as f:
                zip_data = f.read()
            
            # Clean up temp file
            Path('temp_evidence.zip').unlink(missing_ok=True)
            
            logger.info(f"Created evidence ZIP for ticket {ticket_id} with {len(evidence_list)} files")
            return zip_data
            
        except Exception as e:
            logger.error(f"Failed to create evidence ZIP for ticket {ticket_id}: {e}")
            raise
