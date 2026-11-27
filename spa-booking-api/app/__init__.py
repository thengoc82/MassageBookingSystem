import os

from flask import Flask, jsonify, request

from app.config import config
from app.extensions import cors, db, init_redis, jwt, migrate, socketio


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['BOOKING_ACCESS_RUNTIME_ENV'] = config_name
    if config_name == 'production' and any(
        not isinstance(app.config.get(key), str) or len(app.config[key]) < 32
        for key in ('SECRET_KEY', 'JWT_SECRET_KEY')
    ):
        raise RuntimeError('Production requires SECRET_KEY and JWT_SECRET_KEY of at least 32 characters')

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    from app.utils.errors import Unauthorized

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify(Unauthorized().to_dict()), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify(Unauthorized('Invalid access token').to_dict()), 401

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return jsonify(Unauthorized('Access token expired').to_dict()), 401
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

    @app.after_request
    def prevent_booking_response_cache(response):
        if request.path.startswith((
            '/api/bookings', '/api/booking-access', '/api/admin/bookings',
            '/api/therapists/bookings', '/api/admin/customer-restrictions',
        )) or (
            request.path.startswith('/api/admin/shops/')
            and request.path.endswith('/available-slots')
        ) or (
            request.path.startswith('/api/shops/')
            and request.path.endswith('/available-slots')
        ):
            response.headers['Cache-Control'] = 'no-store'
        return response

    return app
