from app import create_app, db
from app.models import *
from app.services.scheduler import start_scheduler
from flask_migrate import upgrade
import logging

app = create_app()

# Run database migrations automatically on startup
with app.app_context():
    try:
        logging.info("Running database migrations...")
        upgrade()
        logging.info("Database migrations completed successfully")
    except Exception as e:
        logging.error(f"Error running migrations: {e}")
        # Don't fail startup if migrations fail - log and continue
        # This allows the app to start even if there are migration issues

# Start the background scheduler for message processing
start_scheduler()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        **{name: obj for name, obj in globals().items() 
           if hasattr(obj, '__tablename__') and not name.startswith('_')}
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
