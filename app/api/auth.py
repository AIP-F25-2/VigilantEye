from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.db.session import get_db
from app.db.models import User
from app.config import settings
from app.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = settings.JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 2
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

@router.post("/signup", response_model=Token)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username exists")
        hashed = pwd_context.hash(payload.password)
        user = User(username=payload.username, hashed_password=hashed)
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token({"sub": user.username})
        logger.info(f"New user signup: {user.username}")
        return Token(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Signup failed: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@router.post("/login", response_model=Token)
def login(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == payload.username).first()
        if not user or not pwd_context.verify(payload.password, user.hashed_password):
            logger.warning("Invalid login attempt")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = create_access_token({"sub": user.username})
        logger.info(f"User logged in: {user.username}")
        return Token(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Server error")
