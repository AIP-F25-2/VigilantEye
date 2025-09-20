from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base
from routers import users, items
from schemas import HealthCheck
from config import settings
from datetime import datetime
import uvicorn

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    description="A REST API backend with FastAPI and MySQL",
    version="1.0.0",
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")

@app.get("/", response_model=dict)
def read_root():
    return {
        "message": "Welcome to VigilantEye API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", response_model=HealthCheck)
def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"
    
    return HealthCheck(
        status="healthy",
        database=database_status,
        timestamp=datetime.now()
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
