from flask import Flask
from .videos import bp as videos_bp
from .segments import bp as segments_bp
from .clips import bp as clips_bp
from .frames import bp as frames_bp
from .autosnap import bp as autosnap_bp
from .record import bp as record_bp

def register_blueprints(app: Flask):
    app.register_blueprint(videos_bp, url_prefix="/api")
    app.register_blueprint(segments_bp, url_prefix="/api")
    app.register_blueprint(clips_bp, url_prefix="/api")
    app.register_blueprint(frames_bp, url_prefix="/api")
    app.register_blueprint(autosnap_bp, url_prefix="/api")
    app.register_blueprint(record_bp, url_prefix="/api")
    app.register_blueprint(audio_bp, url_prefix="/api") 
