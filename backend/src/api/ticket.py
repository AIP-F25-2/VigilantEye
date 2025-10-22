"""Ticket management controller."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.dto.ticket import (
    TicketResponse,
    TicketListResponse,
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketAcknowledgeRequest,
    TicketCloseRequest,
    TicketNoteRequest,
    TicketEvidenceResponse,
    TicketStatsResponse,
)
from src.repositories.ticket import TicketRepository
from src.services.ticket import TicketService
from src.utils.logger import get_logger

from .dependencies import CurrentUser, AdminUser

router = APIRouter(prefix="/tickets", tags=["Tickets"])
logger = get_logger(__name__)


@router.get(
    "/",
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tickets",
    description="Get paginated list of tickets with optional filtering"
)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """List tickets with optional filtering."""
    ticket_repository = TicketRepository(db)
    
    # Convert string filters to enums if provided
    status_filter = None
    priority_filter = None
    
    if status:
        try:
            from src.models.ticket import TicketStatus
            status_filter = TicketStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    if priority:
        try:
            from src.models.ticket import TicketPriority
            priority_filter = TicketPriority(priority.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {priority}"
            )
    
    tickets, total = await ticket_repository.get_all(
        status=status_filter,
        priority=priority_filter,
        skip=skip,
        limit=limit
    )
    
    return TicketListResponse(
        tickets=[TicketResponse.model_validate(ticket) for ticket in tickets],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ticket details",
    description="Get detailed information about a specific ticket"
)
async def get_ticket(
    ticket_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get ticket by ID."""
    ticket_repository = TicketRepository(db)
    ticket = await ticket_repository.get_by_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return TicketResponse.model_validate(ticket)


@router.post(
    "/{ticket_id}/acknowledge",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge ticket",
    description="Acknowledge a ticket to prevent escalation"
)
async def acknowledge_ticket(
    ticket_id: int,
    request: TicketAcknowledgeRequest = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a ticket."""
    ticket_service = TicketService(db)
    
    try:
        ticket = await ticket_service.acknowledge_ticket(
            ticket_id=ticket_id,
            user_id=current_user.id,
            notes=request.notes if request else None
        )
        return TicketResponse.model_validate(ticket)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to acknowledge ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge ticket"
        )


@router.post(
    "/{ticket_id}/close",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Close ticket",
    description="Close a ticket with optional notes"
)
async def close_ticket(
    ticket_id: int,
    request: TicketCloseRequest = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Close a ticket."""
    ticket_service = TicketService(db)
    
    try:
        ticket = await ticket_service.close_ticket(
            ticket_id=ticket_id,
            user_id=current_user.id,
            notes=request.notes if request else None
        )
        return TicketResponse.model_validate(ticket)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to close ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close ticket"
        )


@router.post(
    "/{ticket_id}/note",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Add note to ticket",
    description="Add a note or comment to a ticket"
)
async def add_ticket_note(
    ticket_id: int,
    request: TicketNoteRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a ticket."""
    ticket_service = TicketService(db)
    
    try:
        ticket = await ticket_service.add_note(
            ticket_id=ticket_id,
            user_id=current_user.id,
            note=request.note
        )
        return TicketResponse.model_validate(ticket)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add note to ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add note"
        )


@router.get(
    "/{ticket_id}/evidence",
    response_model=List[TicketEvidenceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get ticket evidence",
    description="Get all evidence files for a ticket"
)
async def get_ticket_evidence(
    ticket_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get evidence for a ticket."""
    ticket_repository = TicketRepository(db)
    
    # Verify ticket exists
    ticket = await ticket_repository.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    evidence = await ticket_repository.get_ticket_evidence(ticket_id)
    return [TicketEvidenceResponse.model_validate(e) for e in evidence]


@router.get(
    "/stats/summary",
    response_model=TicketStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ticket statistics",
    description="Get summary statistics for tickets"
)
async def get_ticket_stats(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get ticket statistics."""
    ticket_service = TicketService(db)
    
    try:
        stats = await ticket_service.get_statistics()
        return TicketStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get ticket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.delete(
    "/{ticket_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete evidence",
    description="Delete evidence file (Admin only)"
)
async def delete_evidence(
    ticket_id: int,
    evidence_id: int,
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete evidence file (Admin only)."""
    ticket_service = TicketService(db)
    
    try:
        await ticket_service.delete_evidence(evidence_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete evidence {evidence_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete evidence"
        )


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete ticket",
    description="Soft delete a ticket (Admin only)"
)
async def soft_delete_ticket(
    ticket_id: int,
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a ticket (Admin only)."""
    ticket_service = TicketService(db)
    
    try:
        await ticket_service.soft_delete_ticket(ticket_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to soft delete ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete ticket"
        )


@router.get(
    "/{ticket_id}/evidence/download",
    summary="Download all evidence",
    description="Download all evidence files as ZIP archive"
)
async def download_all_evidence(
    ticket_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Download all evidence files as ZIP archive."""
    ticket_service = TicketService(db)
    
    try:
        zip_data = await ticket_service.create_evidence_zip(ticket_id)
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=ticket_{ticket_id}_evidence.zip"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create evidence ZIP for ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create evidence archive"
        )
