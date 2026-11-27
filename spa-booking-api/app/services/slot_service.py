from datetime import datetime, timedelta

from app.models.booking import Booking, BookingTherapist
from app.models.shop import Shop
from app.models.therapist import Therapist
from app.services.therapist_service import TherapistService
from app.utils.errors import ResourceNotFound, ValidationError


class SlotService:
    SLOT_INTERVAL = 15

    @staticmethod
    def get_available_slots(shop_id, date, duration, number_of_people, start_time=None, course_ids=None, gender=None, show_therapists=False, include_booking_details=False):
        if type(duration) is not int or duration <= 0:
            raise ValidationError('duration must be a positive integer')
        if type(number_of_people) is not int or number_of_people <= 0:
            raise ValidationError('numberOfPeople must be a positive integer')
        if gender is not None and gender not in ('Male', 'Female'):
            raise ValidationError('gender must be Male or Female')
        if gender and number_of_people != 1:
            raise ValidationError('gender is only available for one guest')
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            if date_obj.isoformat() != date:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValidationError('date must be YYYY-MM-DD')
        if start_time is not None:
            try:
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                if start_time_obj.strftime('%H:%M') != start_time:
                    raise ValueError()
            except (TypeError, ValueError):
                raise ValidationError('startTime must be HH:MM')

        shop = Shop.query.get(shop_id)
        if not shop:
            raise ResourceNotFound('Shop')

        if date_obj < datetime.utcnow().date():
            raise ValidationError('Date cannot be in the past')

        all_therapists = None
        if show_therapists:
            all_therapists = Therapist.query.filter_by(
                shop_id=shop_id, status='active'
            ).all()
            if gender:
                all_therapists = [t for t in all_therapists if t.gender == gender]
            therapist_list = [{
                'therapistId': t.id,
                'name': t.name,
                'gender': t.gender,
            } for t in all_therapists]

        slots = []

        open_time = datetime.combine(date_obj, shop.open_time)
        close_time = datetime.combine(date_obj, shop.close_time)

        current_time = open_time
        if start_time is not None:
            requested_time = datetime.combine(date_obj, start_time_obj)
            minutes_after_open = max(0, int((requested_time - open_time).total_seconds() // 60))
            steps = (minutes_after_open + SlotService.SLOT_INTERVAL - 1) // SlotService.SLOT_INTERVAL
            current_time = open_time + timedelta(minutes=steps * SlotService.SLOT_INTERVAL)

        while shop.status == 'Open' and current_time + timedelta(minutes=duration) <= close_time:
            end_time = current_time + timedelta(minutes=duration)
            st = current_time.time()
            et = end_time.time()

            available_therapists = TherapistService.find_available_therapists(
                shop_id, date_obj, st, et
            )
            if gender:
                available_therapists = [t for t in available_therapists if t.gender == gender]
            available_capacity = len(available_therapists)

            slot = {
                'startTime': current_time.strftime('%H:%M'),
                'endTime': end_time.strftime('%H:%M'),
                'availableCapacity': available_capacity,
            }

            if show_therapists:
                slot['availableTherapistIds'] = [t.id for t in available_therapists]

            if available_capacity >= number_of_people or show_therapists:
                slots.append(slot)

            current_time += timedelta(minutes=SlotService.SLOT_INTERVAL)

        if show_therapists and include_booking_details:
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
                booking_therapist_ids = {bt.therapist_id for bt in bt_map.get(b.id, [])}
                if b.therapist_id:
                    booking_therapist_ids.add(b.therapist_id)

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

        if show_therapists:
            return {'therapists': therapist_list, 'slots': slots}

        return slots
