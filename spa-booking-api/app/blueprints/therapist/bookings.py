from flask import request
from flask_jwt_extended import get_jwt_identity
from app.blueprints.therapist import therapist_bp
from app.utils.decorators import role_required
from app.models.booking import Booking
from app.utils import success_response
from app.utils.errors import ValidationError


@therapist_bp.route('/bookings', methods=['GET'])
@role_required('therapist')
def get_my_bookings():
    identity = get_jwt_identity()
    therapist_id = identity.get('user_id') or identity.get('ref_id')

    if not therapist_id:
        raise ValidationError('Therapist identity not found')

    query = Booking.query.filter_by(therapist_id=therapist_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    date_from = request.args.get('dateFrom')
    if date_from:
        query = query.filter(Booking.booking_date >= date_from)

    date_to = request.args.get('dateTo')
    if date_to:
        query = query.filter(Booking.booking_date <= date_to)

    bookings = query.order_by(Booking.booking_date, Booking.start_time).all()

    data = [{
        'bookingId': b.id,
        'bookingCode': b.booking_code,
        'shopId': b.shop_id,
        'phoneNumber': b.phone_number,
        'bookingDate': b.booking_date.strftime('%Y-%m-%d'),
        'startTime': b.start_time.strftime('%H:%M'),
        'endTime': b.end_time.strftime('%H:%M'),
        'numberOfPeople': b.number_of_people,
        'status': b.status
    } for b in bookings]

    return success_response(data)


@therapist_bp.route('/bookings/<int:booking_id>/checkin', methods=['PATCH'])
@role_required('therapist')
def therapist_checkin(booking_id):
    identity = get_jwt_identity()
    therapist_id = identity.get('user_id') or identity.get('ref_id')

    booking = Booking.query.get(booking_id)
    if not booking:
        from app.utils.errors import ResourceNotFound
        raise ResourceNotFound('Booking')

    if booking.therapist_id != therapist_id:
        from app.utils.errors import Forbidden
        raise Forbidden('This booking is not assigned to you')

    if booking.status != 'Booked':
        from app.utils.errors import BusinessRuleViolation
        raise BusinessRuleViolation('INVALID_CHECKIN_STATUS', 'Only Booked bookings can be checked in')

    booking.status = 'CheckedIn'
    from app.extensions import db
    db.session.commit()

    return success_response({'bookingId': booking.id, 'status': booking.status}, message='Checked in')


@therapist_bp.route('/bookings/<int:booking_id>/checkout', methods=['PATCH'])
@role_required('therapist')
def therapist_checkout(booking_id):
    identity = get_jwt_identity()
    therapist_id = identity.get('user_id') or identity.get('ref_id')

    booking = Booking.query.get(booking_id)
    if not booking:
        from app.utils.errors import ResourceNotFound
        raise ResourceNotFound('Booking')

    if booking.therapist_id != therapist_id:
        from app.utils.errors import Forbidden
        raise Forbidden('This booking is not assigned to you')

    if booking.status != 'CheckedIn':
        from app.utils.errors import BusinessRuleViolation
        raise BusinessRuleViolation('INVALID_CHECKOUT_STATUS', 'Only CheckedIn bookings can be checked out')

    booking.status = 'CheckedOut'
    from app.extensions import db
    db.session.commit()

    return success_response({'bookingId': booking.id, 'status': booking.status}, message='Checked out')
