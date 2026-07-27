from app.models.therapist import Therapist
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import Unauthorized
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

therapist_bp = Blueprint('therapist', __name__)

from app.blueprints.therapist import bookings, schedule  # noqa F401


@therapist_bp.route('/me/profile', methods=['GET'])
@role_required('therapist')
def get_profile():
    identity = get_jwt_identity()

    if not identity:
        raise Unauthorized('Invalid token')

    therapist_id = identity.get('user_id') or identity.get('id')

    if not therapist_id:
        raise Unauthorized('Invalid token')

    therapist = Therapist.query.get(therapist_id)

    if not therapist or therapist.status != 'active':
        raise Unauthorized('Therapist not found or inactive')

    data = {
        'therapistId': therapist.id,
        'name': therapist.name,
        'gender': therapist.gender,
        'phoneNumber': therapist.phone_number,
        'username': therapist.username,
        'status': therapist.status,
        'shopId': therapist.shop_id
    }

    return success_response(data)


@therapist_bp.route('/me/profile', methods=['PATCH'])
@role_required('therapist')
def update_profile():
    identity = get_jwt_identity()

    if not identity:
        raise Unauthorized('Invalid token')

    therapist_id = identity.get('user_id') or identity.get('id')

    if not therapist_id:
        raise Unauthorized('Invalid token')

    therapist = Therapist.query.get(therapist_id)

    if not therapist or therapist.status != 'active':
        raise Unauthorized('Therapist not found or inactive')

    data = request.get_json() or {}

    if 'phoneNumber' in data:
        therapist.phone_number = data['phoneNumber']

    if 'password' in data and data['password']:
        therapist.set_password(data['password'])

    from app.extensions import db
    db.session.commit()

    return success_response({
        'therapistId': therapist.id,
        'name': therapist.name,
        'gender': therapist.gender,
        'phoneNumber': therapist.phone_number,
        'username': therapist.username,
        'status': therapist.status,
        'shopId': therapist.shop_id
    }, message='Profile updated')
