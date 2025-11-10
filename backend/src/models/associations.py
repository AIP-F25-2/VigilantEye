from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Table, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func

from src.app import db

ticket_persons = Table(
    "ticket_persons",
    db.metadata,
    Column("ticket_id", CHAR(36), ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
    Column("person_id", CHAR(36), ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("relevance_score", Float, nullable=True),
    Column("notes", Text, nullable=True),
)

Index("ix_ticket_persons_ticket_id", ticket_persons.c.ticket_id)
Index("ix_ticket_persons_person_id", ticket_persons.c.person_id)

