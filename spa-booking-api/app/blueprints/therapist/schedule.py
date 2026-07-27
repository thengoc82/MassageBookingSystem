from app.blueprints.therapist import therapist_bp
from app.services.therapist_service import TherapistService
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import ValidationError
from flask import request
from flask_jwt_extended import get_jwt_identity


@therapist_bp.route('/me/schedule', methods=['GET'])
@role_required('therapist')
def get_schedule():
    date_from = request.args.get('dateFrom')
    date_to = request.args.get('dateTo')

    if not date_from or not date_to:
        raise ValidationError('dateFrom and dateTo are required')

    identity = get_jwt_identity()
    therapist_id = identity.get('ref_id') or identity.get('user_id')

    schedule = TherapistService.get_schedule(therapist_id, date_from, date_to)

    return success_response(schedule)
