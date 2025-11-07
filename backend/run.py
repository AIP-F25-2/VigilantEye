"""Application entry point for the VigilentEye backend."""

from app import create_app, socketio

app = create_app()


if __name__ == "__main__":
    # TODO: Add task queue initialization and APScheduler setup in Integration Service phase
    socketio.run(app, host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", True))

