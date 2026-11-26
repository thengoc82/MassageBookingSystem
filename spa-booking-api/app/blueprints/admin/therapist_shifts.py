from flask import request

from app.blueprints.admin import admin_bp
from app.services.therapist_shift_service import TherapistShiftService
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import ValidationError


@admin_bp.route('/shops/<int:shop_id>/therapist-shifts', methods=['GET'])
@role_required('admin')
def list_therapist_shifts(shop_id):
    therapist_id = request.args.get('therapistId')
    if therapist_id is not None:
        if not therapist_id.isdigit() or int(therapist_id) <= 0:
            raise ValidationError('therapistId must be a positive integer')
        therapist_id = int(therapist_id)
    return success_response(TherapistShiftService.list(
        shop_id, therapist_id, request.args.get('dayOfWeek')))


@admin_bp.route('/therapist-shifts', methods=['POST'])
@role_required('admin')
def create_therapist_shift():
    return success_response(TherapistShiftService.create(request.get_json(silent=True)),
                            message='Shift created', status_code=201)


@admin_bp.route('/therapist-shifts/<int:shift_id>', methods=['GET'])
@role_required('admin')
def get_therapist_shift(shift_id):
    return success_response(TherapistShiftService.get(shift_id))


@admin_bp.route('/therapist-shifts/<int:shift_id>', methods=['PATCH'])
@role_required('admin')
def update_therapist_shift(shift_id):
    return success_response(TherapistShiftService.update(shift_id, request.get_json(silent=True)),
                            message='Shift updated')


@admin_bp.route('/therapist-shifts/<int:shift_id>', methods=['DELETE'])
@role_required('admin')
def delete_therapist_shift(shift_id):
    return success_response({'shiftId': TherapistShiftService.delete(shift_id)},
                            message='Shift deleted')
