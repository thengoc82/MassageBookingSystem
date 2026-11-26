import re
from datetime import date, datetime, time

from sqlalchemy import or_
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models.booking import Booking, BookingTherapist
from app.models.shop import Shop
from app.models.therapist import Therapist
from app.models.therapist_shift import TherapistShift
from app.utils.errors import APIError, ResourceNotFound, ValidationError


DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
FIELDS = {'dayOfWeek', 'startTime', 'endTime', 'effectiveFrom'}


def _day(value):
    if value not in DAYS:
        raise ValidationError('dayOfWeek must be Monday through Sunday')
    return value


def _time(value, field):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValidationError(f'{field} must be HH:MM')
    return time.fromisoformat(value)


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValidationError('effectiveFrom must be YYYY-MM-DD')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError('effectiveFrom must be a valid date') from exc


def _validate(data, current=None):
    if not isinstance(data, dict):
        raise ValidationError('Request must be a JSON object')
    allowed = FIELDS | ({'therapistId'} if current is None else set())
    if set(data) - allowed:
        raise ValidationError('Unknown shift field')
    if current is None and set(data) != allowed:
        raise ValidationError('therapistId, dayOfWeek, startTime, endTime, and effectiveFrom are required')
    if current is not None and not data:
        raise ValidationError('At least one shift field is required')
    values = {
        'day_of_week': _day(data['dayOfWeek']) if 'dayOfWeek' in data else current.day_of_week,
        'start_time': _time(data['startTime'], 'startTime') if 'startTime' in data else current.start_time,
        'end_time': _time(data['endTime'], 'endTime') if 'endTime' in data else current.end_time,
        'effective_from': _date(data['effectiveFrom']) if 'effectiveFrom' in data else current.effective_from,
    }
    if values['end_time'] <= values['start_time']:
        raise ValidationError('endTime must be after startTime')
    return values


def serialize(shift):
    return {
        'shiftId': shift.id,
        'therapistId': shift.therapist_id,
        'dayOfWeek': shift.day_of_week,
        'startTime': shift.start_time.strftime('%H:%M'),
        'endTime': shift.end_time.strftime('%H:%M'),
        'effectiveFrom': shift.effective_from.isoformat(),
    }


def _shift_write_error(error):
    db.session.rollback()
    if db.engine.dialect.name == 'sqlite' and any(
        marker in str(error.orig).lower() for marker in ('locked', 'busy')
    ):
        raise APIError('SHIFT_CONFLICT', 'Shift schedule is busy; please try again', 409) from error
    raise error


class TherapistShiftService:
    @staticmethod
    def list(shop_id, therapist_id=None, day_of_week=None):
        if db.session.get(Shop, shop_id) is None:
            raise ResourceNotFound('Shop')
        query = TherapistShift.query.join(Therapist).filter(Therapist.shop_id == shop_id)
        if therapist_id is not None:
            query = query.filter(TherapistShift.therapist_id == therapist_id)
        if day_of_week is not None:
            query = query.filter(TherapistShift.day_of_week == _day(day_of_week))
        return [serialize(shift) for shift in query.order_by(
            TherapistShift.therapist_id, TherapistShift.day_of_week,
            TherapistShift.start_time, TherapistShift.id,
        ).all()]

    @staticmethod
    def get(shift_id):
        shift = db.session.get(TherapistShift, shift_id)
        if shift is None:
            raise ResourceNotFound('Shift')
        return serialize(shift)

    @staticmethod
    def _lock(shop_id):
        # Match booking creation and modification: serialize shift writes with
        # availability decisions for the same shop.
        if db.engine.dialect.name == 'sqlite':
            db.session.connection().exec_driver_sql('BEGIN IMMEDIATE')
        else:
            Shop.query.filter_by(id=shop_id).with_for_update().first()

    @staticmethod
    def _overlap(therapist_id, values, exclude_id=None):
        query = TherapistShift.query.filter(
            TherapistShift.therapist_id == therapist_id,
            TherapistShift.day_of_week == values['day_of_week'],
            TherapistShift.start_time < values['end_time'],
            TherapistShift.end_time > values['start_time'],
        )
        if exclude_id is not None:
            query = query.filter(TherapistShift.id != exclude_id)
        if query.first() is not None:
            raise APIError('SHIFT_OVERLAP', 'Therapist shifts overlap', 409)

    @staticmethod
    def _protect_bookings(shift, replacement=None):
        others = TherapistShift.query.filter(
            TherapistShift.therapist_id == shift.therapist_id,
            TherapistShift.id != shift.id,
        ).all()
        bookings = Booking.query.filter(
            Booking.shop_id == shift.therapist.shop_id,
            Booking.booking_date >= datetime.utcnow().date(),
            Booking.status.in_(['Booked', 'CheckedIn']),
            or_(Booking.therapist_id == shift.therapist_id,
                Booking.booking_therapists.any(
                    BookingTherapist.therapist_id == shift.therapist_id)),
        ).all()

        def covers(rule, booking):
            return (rule.day_of_week == booking.booking_date.strftime('%A')
                    and rule.effective_from <= booking.booking_date
                    and rule.start_time <= booking.start_time
                    and rule.end_time >= booking.end_time)

        for booking in bookings:
            if covers(shift, booking) and not (
                any(covers(other, booking) for other in others)
                or (replacement is not None and covers(replacement, booking))
            ):
                raise APIError('SHIFT_BOOKING_CONFLICT',
                               'Shift change would leave an existing booking uncovered', 409)

    @staticmethod
    def create(data):
        values = _validate(data)
        therapist_id = data['therapistId']
        if type(therapist_id) is not int or therapist_id <= 0:
            raise ValidationError('therapistId must be a positive integer')
        try:
            # SQLite must acquire its write lock before any availability read.
            if db.engine.dialect.name == 'sqlite':
                TherapistShiftService._lock(None)
            therapist = db.session.get(Therapist, therapist_id)
            if therapist is None:
                raise ResourceNotFound('Therapist')
            if db.engine.dialect.name != 'sqlite':
                shop_id = therapist.shop_id
                db.session.rollback()
                TherapistShiftService._lock(shop_id)
                therapist = db.session.get(Therapist, therapist_id)
                if therapist is None or therapist.shop_id != shop_id:
                    raise ResourceNotFound('Therapist')
            TherapistShiftService._overlap(therapist_id, values)
            shift = TherapistShift(therapist_id=therapist_id, **values)
            db.session.add(shift)
            db.session.commit()
            return serialize(shift)
        except OperationalError as error:
            _shift_write_error(error)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update(shift_id, data):
        try:
            if db.engine.dialect.name == 'sqlite':
                TherapistShiftService._lock(None)
            shift = db.session.get(TherapistShift, shift_id)
            if shift is None:
                raise ResourceNotFound('Shift')
            if db.engine.dialect.name != 'sqlite':
                shop_id = shift.therapist.shop_id
                db.session.rollback()
                TherapistShiftService._lock(shop_id)
                shift = db.session.get(TherapistShift, shift_id)
                if shift is None or shift.therapist.shop_id != shop_id:
                    raise ResourceNotFound('Shift')
            values = _validate(data, shift)
            TherapistShiftService._overlap(shift.therapist_id, values, shift.id)
            replacement = TherapistShift(therapist_id=shift.therapist_id, **values)
            TherapistShiftService._protect_bookings(shift, replacement)
            for field, value in values.items():
                setattr(shift, field, value)
            db.session.commit()
            return serialize(shift)
        except OperationalError as error:
            _shift_write_error(error)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def delete(shift_id):
        try:
            if db.engine.dialect.name == 'sqlite':
                TherapistShiftService._lock(None)
            shift = db.session.get(TherapistShift, shift_id)
            if shift is None:
                raise ResourceNotFound('Shift')
            if db.engine.dialect.name != 'sqlite':
                shop_id = shift.therapist.shop_id
                db.session.rollback()
                TherapistShiftService._lock(shop_id)
                shift = db.session.get(TherapistShift, shift_id)
                if shift is None or shift.therapist.shop_id != shop_id:
                    raise ResourceNotFound('Shift')
            TherapistShiftService._protect_bookings(shift)
            db.session.delete(shift)
            db.session.commit()
            return shift_id
        except OperationalError as error:
            _shift_write_error(error)
        except Exception:
            db.session.rollback()
            raise
