from flask import jsonify, request

from app.blueprints.admin import admin_bp
from app.services.slot_service import SlotService
from app.utils.decorators import role_required
from app.utils.errors import ValidationError


@admin_bp.route('/shops/<int:shop_id>/available-slots', methods=['GET'])
@role_required('admin')
def get_admin_available_slots(shop_id):
    date = request.args.get('date')
    duration = request.args.get('duration', type=int)
    number_of_people = request.args.get('numberOfPeople', type=int)
    if not date or not duration or not number_of_people:
        raise ValidationError('date, duration, and numberOfPeople are required')
    result = SlotService.get_available_slots(
        shop_id=shop_id,
        date=date,
        duration=duration,
        number_of_people=number_of_people,
        start_time=request.args.get('startTime'),
        course_ids=request.args.get('courseIds'),
        gender=request.args.get('gender'),
        show_therapists=True,
        include_booking_details=True,
    )
    return jsonify({
        'success': True,
        'data': result['slots'],
        'therapists': result['therapists'],
        'therapistBookingDetails': result['therapistBookingDetails'],
        'message': 'Success',
    })
