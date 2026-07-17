from flask import request
from app.blueprints.bookings import bookings_bp
from app.services.booking_service import BookingService
from app.utils import success_response
from app.utils.errors import ResourceNotFound

@bookings_bp.route('', methods=['POST'])
def create_booking():
    data = request.get_json()
    booking = BookingService.create(data)
    
    return success_response({
        'bookingId': booking.id,
        'bookingCode': booking.booking_code,
        'status': booking.status
    }, message='Booking created successfully', status_code=201)

@bookings_bp.route('', methods=['GET'])
def get_bookings():
    filters = {
        'shop_id': request.args.get('shopId', type=int),
        'phone': request.args.get('phone'),
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
    booking = BookingService.get_booking(booking_id)
    
    if not booking:
        raise ResourceNotFound('Booking')
    
    return success_response(booking)

@bookings_bp.route('/<int:booking_id>', methods=['PATCH'])
def update_booking(booking_id):
    data = request.get_json()
    booking = BookingService.update(booking_id, data)
    
    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Booking updated')

@bookings_bp.route('/<int:booking_id>/cancel', methods=['PATCH'])
def cancel_booking(booking_id):
    booking = BookingService.cancel(booking_id)
    
    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Booking cancelled')

@bookings_bp.route('/<int:booking_id>/checkin', methods=['PATCH'])
def checkin_booking(booking_id):
    booking = BookingService.checkin(booking_id)
    
    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Checked in successfully')

@bookings_bp.route('/<int:booking_id>/checkout', methods=['PATCH'])
def checkout_booking(booking_id):
    booking = BookingService.checkout(booking_id)
    
    return success_response({
        'bookingId': booking.id,
        'status': booking.status
    }, message='Checked out successfully')


