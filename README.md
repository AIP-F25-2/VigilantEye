# VigilentEye - AI-Based Multi-Camera Surveillance System

VigilentEye is an AI-driven surveillance platform that unifies multi-camera video ingestion, real-time threat detection, incident ticketing, and comprehensive reporting. The system orchestrates open-source AI models to detect suspicious activity, notify staff via Telegram, and guide operators through escalation workflows.

## Features
- Multi-camera video upload, live streaming, and archival
- AI-powered detection with face recognition, object tracking, audio classification, and LLM-based contextual analysis
- Real-time Telegram alerts with acknowledgment and escalation handling
- Automated ticket lifecycle management with SLA-based rules
- PDF report generation for incident summaries and audit trails
- Role-based access control for staff and administrators

## Technology Stack
- **Backend:** Flask, SQLAlchemy, PyTorch, Transformers, OpenCV, Whisper, YOLOv8
- **Frontend:** React, Tailwind CSS, Socket.IO
- **Databases:** MySQL, Azure Cosmos DB (vector embeddings)
- **Infrastructure:** Docker, Docker Compose

## Prerequisites
- Docker and Docker Compose installed
- Azure Cosmos DB account credentials for vector storage
- Telegram bot token for notifications (placeholder provided)

## Quick Start
1. Clone the repository.
2. Copy `.env.example` to `.env` and provide your environment-specific values.
3. Run `docker-compose up --build` to build images and start all services.
4. Access the frontend at `http://localhost:3000`.
5. Access the backend API at `http://localhost:5000`.

## Project Structure
```
backend/        # Flask REST API, AI modules, database models, services
frontend/       # React single-page application
storage/        # Mounted volumes for videos and evidence artifacts
models/         # Cached open-source AI model weights
docker-compose.yml
README.md
```

## Development
- Backend runs in debug mode with hot reload when executed via Docker Compose.
- Frontend uses the React development server with HMR enabled.
- Backend logs are persisted under `backend/logs/` for review.

## AI Models
All AI models are open-source and cached locally on first use:
- Phi-3-Mini (LLM for situational reasoning)
- YOLOv8x (object and person detection)
- Whisper Base (speech-to-text)
- BLIP-2 (image captioning)
- RetinaFace (face detection)
- YAMNet (audio classification)

Model files are stored under `models/` and reused across restarts.

## Testing
- Backend: `pytest` (with `pytest-cov` and `pytest-flask` support)
- Frontend: `npm test` (Jest + React Testing Library)

## Deployment
- Refer to `DEPLOYMENT.md` (to be created) for production setup guidance including gunicorn, nginx, and multi-stage Docker builds.

## License
This project is released under the MIT License.

## Contributors
- VigilentEye Core Team

