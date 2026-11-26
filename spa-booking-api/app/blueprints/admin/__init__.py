from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from app.blueprints.admin import booking_slots, bookings, courses, customer_restrictions, customers, shops, therapist_shifts, therapists
