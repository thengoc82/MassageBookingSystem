from flask import request, jsonify
from app.blueprints.public import public_bp
from app.services.slot_service import SlotService
from app.utils import success_response
from app.utils.errors import ValidationError

@public_bp.route('/shops/<int:shop_id>/available-slots', methods=['GET'])
def get_available_slots(shop_id):
    date = request.args.get('date')
    duration = request.args.get('duration', type=int)
    number_of_people = request.args.get('numberOfPeople', type=int)
    start_time = request.args.get('startTime')
    course_ids = request.args.get('courseIds')
    gender = request.args.get('gender')
    show_therapists = request.args.get('show_therapists', '').lower() == 'true'
    
    if not date:
        raise ValidationError('date is required')
    
    if not duration:
        raise ValidationError('duration is required')
    
    if not number_of_people:
        raise ValidationError('numberOfPeople is required')
    
    result = SlotService.get_available_slots(
        shop_id=shop_id,
        date=date,
        duration=duration,
        number_of_people=number_of_people,
        start_time=start_time,
        course_ids=course_ids,
        gender=gender,
        show_therapists=show_therapists
    )
    
    if show_therapists:
        return jsonify({
            'success': True,
            'data': result['slots'],
            'therapists': result['therapists'],
            'message': 'Success'
        }), 200
    
    return success_response(result)
