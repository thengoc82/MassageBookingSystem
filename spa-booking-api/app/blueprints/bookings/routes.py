from app.blueprints.bookings import bookings_bp
from app.services.booking_service import BookingService
from app.services.booking_access import booking_identity, require_booking_access, require_customer_phone
from app.models.booking import Booking
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import ResourceNotFound, ValidationError
from flask import request


@bookings_bp.route('', methods=['POST'])
def create_booking():
    data = request.get_json()
    booking = BookingService.create(data)

    therapist_assignments = [{
        'personIndex': bt.person_index,
        'therapistId': bt.therapist.id,
        'therapistName': bt.therapist.name
    } for bt in booking.booking_therapists]

    return success_response({
        'bookingId': booking.id,
        'bookingCode': booking.booking_code,
        'status': booking.status,
        'therapistId': booking.therapist_id,
        'therapistName': booking.therapist.name if booking.therapist else None,
        'therapistAssignments': therapist_assignments
    }, message='Booking created successfully', status_code=201)

@bookings_bp.route('', methods=['GET'])
def get_bookings():
    phone = request.args.get('phone')
    if not phone:
        raise ValidationError('phone is required for customer booking lookup')
    require_customer_phone(phone)
    filters = {
        'shop_id': request.args.get('shopId', type=int),
        'phone': phone,
        'status': request.args.get('status'),
        'date_from': request.args.get('dateFrom'),
        'date_to': request.args.get('dateTo'),
        'page': request.args.get('page', type=int, default=1),
        'size': request.args.get('size', type=int, default=20)
    }

    result = BookingService.get_bookings(filters)

    return success_response(result)

@bookings_bp.route('/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    booking_identity()
    row = Booking.query.get(booking_id)
    if not row:
        raise ResourceNotFound('Booking')
    require_booking_access(row)
    booking = BookingService.get_booking(booking_id)

    return success_response(booking)

@bookings_bp.route('/<int:booking_id>', methods=['PATCH'])
def update_booking(booking_id):
    _authorized_booking(booking_id, write=True)
    data = request.get_json(silent=True)
    booking = BookingService.update(booking_id, data)

    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Booking updated')

@bookings_bp.route('/<int:booking_id>/cancel', methods=['PATCH'])
def cancel_booking(booking_id):
    _authorized_booking(booking_id, write=True)
    booking = BookingService.cancel(booking_id)

    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Booking cancelled')

@bookings_bp.route('/<int:booking_id>/checkin', methods=['PATCH'])
@role_required('admin')
def checkin_booking(booking_id):
    booking = BookingService.checkin(booking_id)

    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Checked in successfully')

@bookings_bp.route('/<int:booking_id>/checkout', methods=['PATCH'])
@role_required('admin')
def checkout_booking(booking_id):
    booking = BookingService.checkout(booking_id)

    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Checked out successfully')


def _authorized_booking(booking_id, *, write=False):
    booking_identity()
    booking = Booking.query.get(booking_id)
    if not booking:
        raise ResourceNotFound('Booking')
    require_booking_access(booking, write=write)
    return booking


