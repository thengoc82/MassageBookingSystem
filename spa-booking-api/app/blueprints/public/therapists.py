from app.blueprints.public import public_bp
from app.services.therapist_service import TherapistService
from app.utils import success_response
from app.utils.errors import ValidationError
from flask import request


@public_bp.route('/shops/<int:shop_id>/available-therapists', methods=['GET'])
def get_available_therapists(shop_id):
    date = request.args.get('date')
    start_time = request.args.get('startTime')
    duration = request.args.get('duration', type=int, default=60)
    gender = request.args.get('gender')

    if not date:
        raise ValidationError('date is required')

    if not start_time:
        raise ValidationError('startTime is required')

    therapists = TherapistService.get_available_therapists(
        shop_id=shop_id,
        date=date,
        start_time=start_time,
        duration=duration,
        gender=gender
    )

    return success_response(therapists)
