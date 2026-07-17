from flask import Blueprint

therapist_bp = Blueprint('therapist', __name__)

from app.blueprints.therapist import schedule
