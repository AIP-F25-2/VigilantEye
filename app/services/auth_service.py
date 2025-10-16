from app.db.session import SessionLocal
from app.db.models import User
from passlib.context import CryptContext
from app.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(username: str, password: str, role: str = "operator"):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            raise ValueError("Username already exists")
        hashed = pwd_context.hash(password)
        u = User(username=username, hashed_password=hashed, role=role)
        db.add(u)
        db.commit()
        db.refresh(u)
        logger.info(f"Created user {username}")
        return u
    finally:
        db.close()

def verify_user(username: str, password: str):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            return None
        if pwd_context.verify(password, u.hashed_password):
            return u
        return None
    finally:
        db.close()
