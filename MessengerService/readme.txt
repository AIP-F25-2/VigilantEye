How it works (flow)

Client calls POST /api/ingest with JSON containing:

type: "text" or "image"

content: text body or image URL (you may extend to accept base64 or multipart)

channel_id: Telegram chat/channel id (e.g. -1001234567890 for channels)

Server creates a DB row OutboundMessage with status=initiated.

Server sends the message to the provided channel immediately using Telegram Bot API. The message contains an inline button "Acknowledge" whose callback payload encodes the internal message id.

After sending, the DB row is updated to status=sent.

Two scheduler jobs are created (APScheduler):

escalate_job runs at created_at + ESCALATE_AFTER_SECONDS (default 15 minutes). If the message is still not acknowledged/closed, the same message is sent to the escalation_channel (from config file) and DB status updated to escalated.

close_job runs at created_at + CLOSE_AFTER_SECONDS (default 1 hour) and sets status to closed unless already closed.

If anyone presses the inline button, Telegram sends a webhook callback_query to /webhook/telegram/<secret>. The webhook handler updates the DB status to acknowledged, logs the user who acknowledged, then immediately marks it closed (per your requirement "make acknowledged to close").

Example curl to ingest a text message
curl -X POST https://your-server.example.com/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "type": "text",
        "content": "ALERT: server down in region X",
        "channel_id": "-100XXXXXXXXXX"
      }'

Example curl to set Telegram webhook

You must set Telegram webhook to https://your-server.example.com/webhook/telegram/<TELEGRAM_WEBHOOK_SECRET>.

curl -X POST "https://api.telegram.org/bot<token>/setWebhook" \
  -d "url=https://your-server.example.com/webhook/telegram/supersecret"


(Replace <token> and supersecret accordingly.)

Notes, trade-offs & improvements (senior-dev points)

Persistent scheduler across restarts: APScheduler in-memory BackgroundScheduler is fine for a single-process deployment. If you need resilience across restarts or multiple processes, use APScheduler with a persistent job store (e.g., SQLAlchemyJobStore) or use a distributed task queue like Celery + Redis/RabbitMQ and schedule tasks there.

Database migrations: Use Alembic / Flask-Migrate for schema evolution; here Base.metadata.create_all is a simple convenience for quick start.

Security: protect your webhook endpoint (we used a path secret). For production use TLS (HTTPS) and validate Telegram secret_token header (Telegram supports setting secret token on setWebhook).

Image payloads: I assumed image URLs. If you accept image uploads, accept multipart/form-data and persist the file (S3, disk), then send via sendPhoto uploading the file bytes.

Retries & error handling: Add robust retry/backoff for Telegram API calls, and mark DB meta with errors. Consider adding a dead-letter table for failed sends.

Idempotency: Make ingest idempotent if clients retry; accept an external client_id to dedupe.

Logging & monitoring: Add structured logs, metrics (e.g. Prometheus), and alerts for failures.

Testing: Add unit tests for scheduler and webhook logic, and integration tests hitting a test Telegram bot.

Concurrency: If deploying under multiple Flask workers (e.g., Gunicorn), ensure the scheduler runs only in one worker (e.g., run scheduler in a separate process).

Permissions: Bot must be an admin to post to channels and receive callback queries; adding inline buttons to channel messages is allowed if bot posted the message.

DB session handling: I used simple SessionLocal get/commit/close patterns; adapt to context managers for better reliability.

Quick run instructions

Create a virtualenv, install requirements:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


Create .env from .env.example and fill values (DB URI, token, webhook secret).

Create DB and run python snippet to create tables or use Alembic.

Start app:

python app.py


Set Telegram webhook:

curl -F "url=https://your-public-host/webhook/telegram/<WEBHOOK_SECRET>" https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook


Send a test ingest request with the curl example above.

If you want, I can:

generate the full repo as a zip you can download (need to create files here), or

extend the design to use Celery + Redis for scheduling (recommended for production), or

implement persistent jobstore for APScheduler with SQLAlchemy so jobs survive restarts.

Which of those would you like next?