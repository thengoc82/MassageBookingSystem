from flask import request

from app.blueprints.public import public_bp
from app.services.booking_access import request_code, verify_code
from app.utils import success_response
from app.utils.errors import ValidationError


@public_bp.route('/booking-access/challenges', methods=['POST'])
def create_booking_access_challenge():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('A JSON phone number is required')
    delivery = request_code(data.get('phoneNumber'))
    return success_response({'delivery': delivery}, message='Verification code generated')


@public_bp.route('/booking-access/verifications', methods=['POST'])
def verify_booking_access_challenge():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('A JSON phone number and code are required')
    token = verify_code(data.get('phoneNumber'), data.get('code'))
    return success_response({'accessToken': token}, message='Phone verified')
