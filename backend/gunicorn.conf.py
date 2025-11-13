# Gunicorn configuration file for production WSGI server

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000

# Timeout settings
timeout = 300  # 5 minutes for long AI analysis
keepalive = 2

# Worker lifecycle
max_requests = 1000  # Restart worker after N requests (prevent memory leaks)
max_requests_jitter = 50  # Add randomness to max_requests
preload_app = True  # Load app before forking workers (shares memory)

# Logging
accesslog = "-"  # Log to stdout (Docker captures)
errorlog = "-"   # Log to stderr
loglevel = "info"  # debug, info, warning, error, critical
capture_output = True  # Capture stdout/stderr from app
enable_stdio_inheritance = True  # Inherit stdio from parent

# Application
wsgi_app = "src.app:create_app()"


def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn server...")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn server...")


def worker_int(worker):
    """Called when a worker receives INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

