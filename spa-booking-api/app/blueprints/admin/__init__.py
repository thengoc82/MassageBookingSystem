from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from app.blueprints.admin import booking_slots, bookings, courses, customers, shops, therapist_shifts, therapists
