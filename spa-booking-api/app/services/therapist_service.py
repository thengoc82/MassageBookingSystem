from datetime import datetime, time, timedelta

from app.extensions import db
from app.models.booking import Booking, BookingTherapist
from app.models.therapist import Therapist
from app.models.therapist_shift import TherapistShift


class TherapistService:

    @staticmethod
    def find_available_therapists(shop_id, date, start_time, end_time):
        all_therapists = Therapist.query.filter_by(
            shop_id=shop_id,
            status='active'
        ).all()

        available = []
        for therapist in all_therapists:
            if TherapistService.is_available(therapist.id, date, start_time, end_time):
                available.append(therapist)

        return available

    @staticmethod
    def count_available_capacity(shop_id, date, start_time, end_time):
        total = TherapistService._count_active_therapists(shop_id, date, start_time, end_time)

        booked = Booking.query.filter(
            Booking.shop_id == shop_id,
            Booking.booking_date == date,
            Booking.status.in_(['Booked', 'CheckedIn']),
            db.or_(
                db.and_(Booking.start_time < end_time, Booking.end_time > start_time)
            )
        ).count()

        return total - booked

    @staticmethod
    def _count_active_therapists(shop_id, date, start_time, end_time):
        day_of_week = date.strftime('%A')
        return TherapistShift.query.join(Therapist).filter(
            Therapist.shop_id == shop_id,
            Therapist.status == 'active',
            TherapistShift.day_of_week == day_of_week,
            TherapistShift.effective_from <= date,
            TherapistShift.start_time <= start_time,
            TherapistShift.end_time >= end_time
        ).count()

    @staticmethod
    def is_available(therapist_id, date, start_time, end_time):
        if not TherapistService._has_shift_coverage(therapist_id, date, start_time, end_time):
            return False

        overlapping_bookings = db.session.query(BookingTherapist).join(
            Booking, Booking.id == BookingTherapist.booking_id
        ).filter(
            BookingTherapist.therapist_id == therapist_id,
            Booking.booking_date == date,
            Booking.status.in_(['Booked', 'CheckedIn']),
            db.or_(
                db.and_(Booking.start_time < end_time, Booking.end_time > start_time)
            )
        ).count()

        return overlapping_bookings == 0

    @staticmethod
    def _has_shift_coverage(therapist_id, date, start_time, end_time):
        day_of_week = date.strftime('%A')

        shifts = TherapistShift.query.filter(
            TherapistShift.therapist_id == therapist_id,
            TherapistShift.day_of_week == day_of_week,
            TherapistShift.effective_from <= date
        ).all()

        if not shifts:
            return False

        for shift in shifts:
            if shift.start_time <= start_time and shift.end_time >= end_time:
                return True

        return False

    @staticmethod
    def get_available_therapists(shop_id, date, start_time, duration=None, gender=None):
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        start = datetime.strptime(start_time, '%H:%M').time()

        if duration:
            start_dt = datetime.combine(date_obj, start)
            end_dt = start_dt + timedelta(minutes=duration)
            end = end_dt.time()
        else:
            end = time(23, 59)

        therapists = Therapist.query.filter_by(
            shop_id=shop_id,
            status='active'
        )

        if gender:
            therapists = therapists.filter(Therapist.gender == gender)

        result = []
        for therapist in therapists.all():
            available = TherapistService.is_available(therapist.id, date_obj, start, end)
            result.append({
                'therapistId': therapist.id,
                'name': therapist.name,
                'gender': therapist.gender,
                'isAvailable': available
            })

        return result

    @staticmethod
    def get_schedule(therapist_id, date_from, date_to):
        bookings = Booking.query.filter(
            Booking.therapist_id == therapist_id,
            Booking.booking_date >= date_from,
            Booking.booking_date <= date_to,
            Booking.status.in_(['Booked', 'CheckedIn'])
        ).order_by(Booking.booking_date, Booking.start_time).all()

        return [{
            'bookingId': b.id,
            'bookingCode': b.booking_code,
            'date': b.booking_date.strftime('%Y-%m-%d'),
            'startTime': b.start_time.strftime('%H:%M'),
            'endTime': b.end_time.strftime('%H:%M'),
            'customerPhone': b.phone_number,
            'status': b.status
        } for b in bookings]
