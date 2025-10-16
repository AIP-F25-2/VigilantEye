from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db.models import Ticket, Evidence
from app.db.session import get_db
from app.logger import logger
from typing import Optional

router = APIRouter(prefix="/data", tags=["CRUD"])

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=403, detail="Authorization header missing")
    # expected: "Bearer <token>" — for demo we don't decode here; auth middleware handles in real app
    token = authorization.split(" ")[-1]
    # TODO: decode token and validate — simplified here
    return token

@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    try:
        tickets = db.query(Ticket).all()
        logger.info(f"Fetched {len(tickets)} tickets by token")
        return tickets
    except Exception as e:
        logger.exception(f"Error listing tickets: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@router.get("/evidence")
def list_evidence(db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    try:
        evidence = db.query(Evidence).all()
        logger.info(f"Fetched {len(evidence)} evidence records")
        return evidence
    except Exception as e:
        logger.exception(f"Error listing evidence: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@router.delete("/ticket/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Ticket not found")
        db.delete(ticket)
        db.commit()
        logger.info(f"Deleted ticket {ticket_id}")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Server error")
