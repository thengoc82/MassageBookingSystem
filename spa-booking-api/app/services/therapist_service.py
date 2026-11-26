from datetime import datetime, time, timedelta

from app.extensions import db
from app.models.booking import Booking, BookingTherapist
from app.models.therapist import Therapist
from app.models.therapist_shift import TherapistShift


class TherapistService:

    @staticmethod
    def find_available_therapists(shop_id, date, start_time, end_time, exclude_booking_id=None):
        available_ids = TherapistService._available_therapist_ids(
            shop_id, date, start_time, end_time, exclude_booking_id
        )
        if not available_ids:
            return []
        return Therapist.query.filter(
            Therapist.id.in_(available_ids)
        ).order_by(Therapist.id).all()

    @staticmethod
    def count_available_capacity(shop_id, date, start_time, end_time):
        return len(TherapistService._available_therapist_ids(
            shop_id, date, start_time, end_time
        ))

    @staticmethod
    def _available_therapist_ids(shop_id, date, start_time, end_time, exclude_booking_id=None):
        day_of_week = date.strftime('%A')
        covering_ids = {
            therapist_id for (therapist_id,) in db.session.query(
                TherapistShift.therapist_id
            ).join(Therapist).filter(
                Therapist.shop_id == shop_id,
                Therapist.status == 'active',
                TherapistShift.day_of_week == day_of_week,
                TherapistShift.effective_from <= date,
                TherapistShift.start_time <= start_time,
                TherapistShift.end_time >= end_time,
            ).distinct().all()
        }
        if not covering_ids:
            return set()

        overlap = [
            Booking.shop_id == shop_id,
            Booking.booking_date == date,
            Booking.status.in_(['Booked', 'CheckedIn']),
            Booking.start_time < end_time,
            Booking.end_time > start_time,
        ]
        if exclude_booking_id is not None:
            overlap.append(Booking.id != exclude_booking_id)
        # The legacy pointer and per-guest rows describe assignments to the same
        # booking. A set counts each occupied therapist only once.
        occupied_ids = {
            therapist_id for (therapist_id,) in db.session.query(
                Booking.therapist_id
            ).filter(*overlap, Booking.therapist_id.isnot(None)).all()
        }
        occupied_ids.update(
            therapist_id for (therapist_id,) in db.session.query(
                BookingTherapist.therapist_id
            ).join(Booking, Booking.id == BookingTherapist.booking_id).filter(
                *overlap
            ).all()
        )
        return covering_ids - occupied_ids

    @staticmethod
    def is_available(therapist_id, date, start_time, end_time):
        therapist = db.session.get(Therapist, therapist_id)
        return bool(therapist and therapist.id in TherapistService._available_therapist_ids(
            therapist.shop_id, date, start_time, end_time
        ))

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

        available_ids = TherapistService._available_therapist_ids(
            shop_id, date_obj, start, end
        )
        result = []
        for therapist in therapists.all():
            result.append({
                'therapistId': therapist.id,
                'name': therapist.name,
                'gender': therapist.gender,
                'isAvailable': therapist.id in available_ids
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
