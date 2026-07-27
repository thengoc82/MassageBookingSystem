from flask import Blueprint

bookings_bp = Blueprint('bookings', __name__)

from app.blueprints.bookings import routes  # noqa F401
