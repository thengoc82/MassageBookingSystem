from flask import request
from app.blueprints.admin import admin_bp
from app.utils.decorators import role_required
from app.models.booking import Booking
from app.extensions import db
from app.utils import success_response
from app.utils.errors import ResourceNotFound, BusinessRuleViolation


@admin_bp.route('/bookings', methods=['GET'])
@role_required('admin')
def list_bookings():
    query = Booking.query

    shop_id = request.args.get('shopId', type=int)
    if shop_id:
        query = query.filter_by(shop_id=shop_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    phone = request.args.get('phone')
    if phone:
        query = query.filter_by(phone_number=phone)

    date_from = request.args.get('dateFrom')
    if date_from:
        query = query.filter(Booking.booking_date >= date_from)

    date_to = request.args.get('dateTo')
    if date_to:
        query = query.filter(Booking.booking_date <= date_to)

    bookings = query.order_by(Booking.booking_date.desc(), Booking.start_time).all()

    data = []
    for b in bookings:
        assignments = [{
            'personIndex': bt.person_index,
            'therapistId': bt.therapist.id,
            'therapistName': bt.therapist.name
        } for bt in b.booking_therapists]
        data.append({
            'bookingId': b.id,
            'bookingCode': b.booking_code,
            'shopId': b.shop_id,
            'phoneNumber': b.phone_number,
            'bookingDate': b.booking_date.strftime('%Y-%m-%d'),
            'startTime': b.start_time.strftime('%H:%M'),
            'endTime': b.end_time.strftime('%H:%M'),
            'numberOfPeople': b.number_of_people,
            'therapistId': b.therapist_id,
            'therapistName': b.therapist.name if b.therapist else None,
            'therapistAssignments': assignments,
            'status': b.status
        })

    return success_response(data)


@admin_bp.route('/bookings/<int:booking_id>/cancel', methods=['PATCH'])
@role_required('admin')
def admin_cancel(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        raise ResourceNotFound('Booking')

    if booking.status != 'Booked':
        raise BusinessRuleViolation('INVALID_CANCEL_STATUS', 'Only Booked bookings can be cancelled')

    booking.status = 'Cancelled'
    db.session.commit()

    return success_response({'bookingId': booking.id, 'status': booking.status}, message='Booking cancelled')


@admin_bp.route('/bookings/<int:booking_id>/checkin', methods=['PATCH'])
@role_required('admin')
def admin_checkin(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        raise ResourceNotFound('Booking')

    if booking.status != 'Booked':
        raise BusinessRuleViolation('INVALID_CHECKIN_STATUS', 'Only Booked bookings can be checked in')

    booking.status = 'CheckedIn'
    db.session.commit()

    return success_response({'bookingId': booking.id, 'status': booking.status}, message='Checked in')


@admin_bp.route('/bookings/<int:booking_id>/checkout', methods=['PATCH'])
@role_required('admin')
def admin_checkout(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        raise ResourceNotFound('Booking')

    if booking.status != 'CheckedIn':
        raise BusinessRuleViolation('INVALID_CHECKOUT_STATUS', 'Only CheckedIn bookings can be checked out')

    booking.status = 'CheckedOut'
    db.session.commit()

    return success_response({'bookingId': booking.id, 'status': booking.status}, message='Checked out')
