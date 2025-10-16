from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from app.db.session import Base, engine, get_db
from app.db import entities as dbmodels
from app.logger import logger
from app.services.extractor import extract_from_video_bytes
from app.services.analyzer import analyze_artifact_pair
from app.services.ticketing import create_ticket
from app.utils.cleanup import start_cleanup_thread
from app.api import auth as auth_router, routes as data_routes, middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from sqlalchemy.exc import SQLAlchemyError

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Surveillance Pipeline")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(middleware.log_requests)

# Include routers
app.include_router(auth_router.router)
app.include_router(data_routes.router)

@app.on_event("startup")
def on_startup():
    logger.info("Starting app and background workers")
    start_cleanup_thread()

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        content = await file.read()
        extraction = extract_from_video_bytes(content)
        audio_id = extraction.get("audio_artifact_id")
        frames = extraction.get("frames", [])

        # analyze each frame with parallel models
        suspicious_artifact_ids = []
        for f in frames:
            aid = f.get("artifact_id")
            analysis = analyze_artifact_pair(aid, audio_id)
            if analysis.get("suspicious"):
                suspicious_artifact_ids.append(aid)

        if suspicious_artifact_ids:
            t = create_ticket(suspicious_artifact_ids, llm_decision="automated")
            return {"ticket_id": t.id, "suspicious_count": len(suspicious_artifact_ids)}

        return {"status": "ok", "frames_analyzed": len(frames)}
    except Exception as e:
        logger.exception(f"Upload processing failed: {e}")
        raise HTTPException(status_code=500, detail="Processing failed")

@app.get("/")
def health():
    return JSONResponse({"status": "ok"})

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
