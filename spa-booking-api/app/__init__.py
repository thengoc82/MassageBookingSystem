import os

from flask import Flask

from app.config import config
from app.extensions import cors, db, init_redis, jwt, migrate, socketio


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*')
    cors.init_app(app)
    init_redis(app)

    from app.blueprints.admin import admin_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.bookings import bookings_bp
    from app.blueprints.public import public_bp
    from app.blueprints.setup import setup_bp
    from app.blueprints.therapist import therapist_bp
    from app.blueprints.voice_booking import voice_bp
    from app.models import (
        Booking,
        BookingAddon,
        BookingService,
        Course,
        Customer,
        CustomerRestriction,
        Shop,
        Therapist,
        TherapistShift,
        User,
    )

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(public_bp, url_prefix='/api')
    app.register_blueprint(bookings_bp, url_prefix='/api/bookings')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(therapist_bp, url_prefix='/api/therapists')
    app.register_blueprint(voice_bp, url_prefix='/api/voice')
    app.register_blueprint(setup_bp, url_prefix='/api')

    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    return app
