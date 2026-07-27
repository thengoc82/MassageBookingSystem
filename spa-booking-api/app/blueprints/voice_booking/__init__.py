from flask import Blueprint

voice_bp = Blueprint('voice_booking', __name__)

from app.blueprints.voice_booking import routes  # noqa F401
