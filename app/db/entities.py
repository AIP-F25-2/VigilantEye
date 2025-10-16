from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from .session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="operator", nullable=False)

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(String, primary_key=True, index=True)  # store uuid string
    type = Column(String, nullable=False)  # 'image' | 'audio'
    path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    evidence = Column(JSON, default=list)  # list of artifact ids
    llm_decision = Column(String, nullable=True)

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    artifact_id = Column(String, ForeignKey("artifacts.id"))
    meta_data = Column(JSON, default={})

class FaceVector(Base):
    __tablename__ = "face_vectors"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String, index=True)
    artifact_id = Column(String, ForeignKey("artifacts.id"))
    vector = Column(LargeBinary)  # store numpy.tobytes()
    created_at = Column(DateTime(timezone=True), server_default=func.now())
