from datetime import datetime, timedelta, time
from app.models.shop import Shop
from app.models.therapist import Therapist
from app.models.booking import Booking, BookingTherapist
from app.services.therapist_service import TherapistService
from app.extensions import db
from app.utils.errors import ResourceNotFound, ValidationError

class SlotService:
    SLOT_INTERVAL = 15

    @staticmethod
    def get_available_slots(shop_id, date, duration, number_of_people, start_time=None, course_ids=None, gender=None, show_therapists=False):
        shop = Shop.query.get(shop_id)
        if not shop:
            raise ResourceNotFound('Shop')

        date_obj = datetime.strptime(date, '%Y-%m-%d').date()

        if date_obj < datetime.utcnow().date():
            raise ValidationError('Date cannot be in the past')

        all_therapists = None
        if show_therapists:
            all_therapists = Therapist.query.filter_by(
                shop_id=shop_id, status='active'
            ).all()
            therapist_list = [{
                'therapistId': t.id,
                'name': t.name,
                'gender': t.gender,
            } for t in all_therapists]

        slots = []

        open_time = datetime.combine(date_obj, shop.open_time)
        close_time = datetime.combine(date_obj, shop.close_time)

        current_time = open_time
        if start_time:
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            current_time = datetime.combine(date_obj, start_time_obj)

        while current_time + timedelta(minutes=duration) <= close_time:
            end_time = current_time + timedelta(minutes=duration)
            st = current_time.time()
            et = end_time.time()

            available_capacity = TherapistService.count_available_capacity(
                shop_id, date_obj, st, et
            )

            slot = {
                'startTime': current_time.strftime('%H:%M'),
                'endTime': end_time.strftime('%H:%M'),
                'availableCapacity': available_capacity,
            }

            if show_therapists:
                available_ids = []
                for t in all_therapists:
                    if TherapistService.is_available(t.id, date_obj, st, et):
                        available_ids.append(t.id)
                slot['availableTherapistIds'] = available_ids

            if available_capacity >= number_of_people or show_therapists:
                slots.append(slot)

            current_time += timedelta(minutes=SlotService.SLOT_INTERVAL)

        if show_therapists:
            bookings_q = Booking.query.filter(
                Booking.shop_id == shop_id,
                Booking.booking_date == date_obj,
                Booking.status.in_(['Booked', 'CheckedIn']),
            ).all()

            bt_q = BookingTherapist.query.join(
                Booking, Booking.id == BookingTherapist.booking_id
            ).filter(
                Booking.shop_id == shop_id,
                Booking.booking_date == date_obj,
                Booking.status.in_(['Booked', 'CheckedIn']),
            ).all()

            therapist_booking_details = {}
            for t in all_therapists:
                therapist_booking_details[t.id] = []

            bt_map = {}
            for bt in bt_q:
                if bt.booking_id not in bt_map:
                    bt_map[bt.booking_id] = []
                bt_map[bt.booking_id].append(bt)

            for b in bookings_q:
                booking_therapist_ids = [bt.therapist_id for bt in bt_map.get(b.id, [])]
                # TODO: remove this fallback after a complete BookingTherapist backfill migration
                if not booking_therapist_ids and b.therapist_id:
                    booking_therapist_ids = [b.therapist_id]

                sorted_services = sorted(b.services, key=lambda s: s.person_index) if b.services else []
                course_name = sorted_services[0].course.name if sorted_services and sorted_services[0].course else None

                booking_detail = {
                    'bookingId': b.id,
                    'bookingCode': b.booking_code,
                    'startTime': b.start_time.strftime('%H:%M'),
                    'endTime': b.end_time.strftime('%H:%M'),
                    'courseName': course_name,
                    'numberOfPeople': b.number_of_people,
                }

                for tid in booking_therapist_ids:
                    if tid in therapist_booking_details:
                        therapist_booking_details[tid].append(booking_detail)

            return {'therapists': therapist_list, 'slots': slots, 'therapistBookingDetails': therapist_booking_details}

        return slots
