import json
import random
import string
from datetime import datetime, timedelta
from app.models.booking import Booking, BookingService as BookingServiceModel, BookingAddon
from app.models.therapist import Therapist
from app.services.customer_service import CustomerService
from app.extensions import db
from app.utils.errors import ResourceNotFound, BusinessRuleViolation, ValidationError

class BookingService:
    @staticmethod
    def create(data):
        phone_number = data.get('phoneNumber')
        if not phone_number:
            raise ValidationError('phoneNumber is required')

        eligibility = CustomerService.check_eligibility(phone_number)
        if not eligibility['isEligible']:
            raise BusinessRuleViolation('CUSTOMER_BLOCKED', 'Customer on NG List')

        shop_id = data.get('shopId')
        booking_date_str = data.get('bookingDate')
        start_time_str = data.get('startTime')
        duration = data.get('duration')
        number_of_people = data.get('numberOfPeople', 1)

        if not all([shop_id, booking_date_str, start_time_str, duration]):
            raise ValidationError('shopId, bookingDate, startTime, and duration are required')

        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()

        start_datetime = datetime.combine(booking_date, start_time)
        end_datetime = start_datetime + timedelta(minutes=duration)
        end_time = end_datetime.time()

        therapist_preference_type = data.get('therapistPreferenceType')
        therapist_preference_value = data.get('therapistPreferenceValue')

        try:
            db.session.begin_nested()

            assigned_therapist = None

            if number_of_people == 1 and therapist_preference_type == 'specific' and therapist_preference_value:
                try:
                    therapist_id = int(therapist_preference_value)
                    therapist = db.session.query(Therapist).filter(
                        Therapist.id == therapist_id,
                        Therapist.shop_id == shop_id,
                        Therapist.status == 'active'
                    ).with_for_update(skip_locked=True).first()

                    if not therapist:
                        raise BusinessRuleViolation('SLOT_UNAVAILABLE', 'Requested therapist is no longer available')

                    if not BookingService._is_therapist_free(therapist.id, booking_date, start_time, end_time):
                        raise BusinessRuleViolation('SLOT_UNAVAILABLE', 'Requested therapist is no longer available at this time')

                    assigned_therapist = therapist

                except ValueError:
                    raise ValidationError('Invalid therapist ID')

            elif number_of_people == 1 and therapist_preference_type == 'gender' and therapist_preference_value:
                therapist = BookingService._lock_available_therapist_by_gender(
                    shop_id, booking_date, start_time, end_time,
                    therapist_preference_value
                )
                if not therapist:
                    raise BusinessRuleViolation('SLOT_UNAVAILABLE', f'No {therapist_preference_value} therapist available at this time')
                assigned_therapist = therapist

            elif number_of_people == 1 and (not therapist_preference_type or therapist_preference_type == 'no_preference'):
                therapist = BookingService._lock_least_loaded_therapist(
                    shop_id, booking_date, start_time, end_time
                )
                assigned_therapist = therapist

            else:
                for i in range(number_of_people):
                    therapist = BookingService._lock_least_loaded_therapist(
                        shop_id, booking_date, start_time, end_time
                    )
                    if not therapist:
                        available = BookingService._count_available_therapists(
                            shop_id, booking_date, start_time, end_time
                        )
                        raise BusinessRuleViolation('INSUFFICIENT_THERAPISTS',
                            f'Need {number_of_people} therapists, only {available} available')
                    if assigned_therapist is None:
                        assigned_therapist = therapist

            customer = CustomerService.find_or_create(phone_number)

            booking_code = BookingService._generate_booking_code()

            booking = Booking(
                booking_code=booking_code,
                shop_id=shop_id,
                customer_id=customer.id,
                phone_number=phone_number,
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                number_of_people=number_of_people,
                therapist_id=assigned_therapist.id if assigned_therapist else None,
                status='Booked'
            )

            db.session.add(booking)
            db.session.flush()

            if not data.get('services'):
                course_id = data.get('courseId')
                if not course_id:
                    raise ValidationError('courseId or services is required')
                service_data = [{
                    'personIndex': i + 1,
                    'courseId': course_id
                } for i in range(number_of_people)]
            else:
                service_data = data.get('services', [])

            for service in service_data:
                booking_service = BookingServiceModel(
                    booking_id=booking.id,
                    person_index=service['personIndex'],
                    course_id=service['courseId']
                )
                db.session.add(booking_service)

            for addon in data.get('addOns', []):
                booking_addon = BookingAddon(
                    booking_id=booking.id,
                    person_index=addon['personIndex'],
                    course_id=addon['courseId']
                )
                db.session.add(booking_addon)

            core_keys = {'phoneNumber', 'shopId', 'bookingDate', 'startTime', 'duration', 'numberOfPeople', 'courseId', 'services', 'addOns', 'therapistPreferenceType', 'therapistPreferenceValue'}
            preferences = {k: v for k, v in data.items() if k not in core_keys and v is not None}
            if preferences:
                booking.preferences_json = json.dumps(preferences, ensure_ascii=False)

            pos_result = BookingService._call_pos_api(booking)

            if not pos_result['success']:
                raise BusinessRuleViolation('POS_ERROR', pos_result.get('message', 'POS integration failed'))

            db.session.commit()

            return booking

        except (BusinessRuleViolation, ValidationError, ResourceNotFound) as e:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            raise BusinessRuleViolation('BOOKING_FAILED', f'Failed to create booking: {str(e)}')

    @staticmethod
    def _lock_least_loaded_therapist(shop_id, date, start_time, end_time):
        therapist = db.session.query(
            Therapist,
            db.func.coalesce(db.func.sum(
                db.func.extract('epoch', Booking.end_time) - db.func.extract('epoch', Booking.start_time)
            ), 0).label('workload')
        ).filter(
            Therapist.shop_id == shop_id,
            Therapist.status == 'active'
        ).outerjoin(
            Booking,
            db.and_(
                Booking.therapist_id == Therapist.id,
                Booking.booking_date == date,
                Booking.status.in_(['Booked', 'CheckedIn'])
            )
        ).group_by(Therapist.id).order_by(
            db.text('workload ASC'),
            Therapist.id.asc()
        ).with_for_update(skip_locked=True).first()

        if not therapist:
            return None

        if not BookingService._is_therapist_free(therapist.Therapist.id, date, start_time, end_time):
            return None

        return therapist.Therapist

    @staticmethod
    def _lock_available_therapist_by_gender(shop_id, date, start_time, end_time, gender):
        therapist = db.session.query(
            Therapist,
            db.func.coalesce(db.func.sum(
                db.func.extract('epoch', Booking.end_time) - db.func.extract('epoch', Booking.start_time)
            ), 0).label('workload')
        ).filter(
            Therapist.shop_id == shop_id,
            Therapist.status == 'active',
            Therapist.gender == gender
        ).outerjoin(
            Booking,
            db.and_(
                Booking.therapist_id == Therapist.id,
                Booking.booking_date == date,
                Booking.status.in_(['Booked', 'CheckedIn'])
            )
        ).group_by(Therapist.id).order_by(
            db.text('workload ASC'),
            Therapist.id.asc()
        ).with_for_update(skip_locked=True).first()

        if not therapist:
            return None

        if not BookingService._is_therapist_free(therapist.Therapist.id, date, start_time, end_time):
            return None

        return therapist.Therapist

    @staticmethod
    def _count_available_therapists(shop_id, date, start_time, end_time):
        from app.models.therapist_shift import TherapistShift
        day_of_week = date.strftime('%A')

        all_therapists = Therapist.query.filter_by(shop_id=shop_id, status='active').all()
        available = 0

        for therapist in all_therapists:
            shift = TherapistShift.query.filter(
                TherapistShift.therapist_id == therapist.id,
                TherapistShift.day_of_week == day_of_week,
                TherapistShift.effective_from <= date
            ).first()

            if not shift:
                continue
            if not (shift.start_time <= start_time and shift.end_time >= end_time):
                continue

            if BookingService._is_therapist_free(therapist.id, date, start_time, end_time):
                available += 1

        return available

    @staticmethod
    def _is_therapist_free(therapist_id, date, start_time, end_time):
        overlapping = db.session.query(Booking).filter(
            Booking.therapist_id == therapist_id,
            Booking.booking_date == date,
            Booking.status.in_(['Booked', 'CheckedIn']),
            db.or_(
                db.and_(Booking.start_time < end_time, Booking.end_time > start_time)
            )
        ).count()

        if overlapping > 0:
            return False

        return True

    @staticmethod
    def _call_pos_api(booking):
        return {
            'success': True,
            'posBookingId': f'POS-{booking.booking_code}',
            'message': 'Booking created in POS'
        }

    @staticmethod
    def _generate_booking_code():
        date_str = datetime.utcnow().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f'BK{date_str}{random_str}'

    @staticmethod
    def get_bookings(filters):
        query = Booking.query

        if filters.get('shop_id'):
            query = query.filter_by(shop_id=filters['shop_id'])

        if filters.get('phone'):
            query = query.filter_by(phone_number=filters['phone'])

        if filters.get('status'):
            query = query.filter_by(status=filters['status'])

        if filters.get('date_from'):
            date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
            query = query.filter(Booking.booking_date >= date_from)

        if filters.get('date_to'):
            date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
            query = query.filter(Booking.booking_date <= date_to)

        page = filters.get('page', 1)
        size = filters.get('size', 20)

        total = query.count()
        bookings = query.offset((page - 1) * size).limit(size).all()

        data = [BookingService._booking_to_dict(b) for b in bookings]

        return {
            'data': data,
            'pagination': {
                'page': page,
                'size': size,
                'total': total,
                'totalPages': (total + size - 1) // size
            }
        }

    @staticmethod
    def get_booking(booking_id):
        booking = Booking.query.get(booking_id)
        if not booking:
            raise ResourceNotFound('Booking')

        return BookingService._booking_to_dict(booking, detailed=True)

    @staticmethod
    def update(booking_id, data):
        booking = Booking.query.get(booking_id)
        if not booking:
            raise ResourceNotFound('Booking')

        if booking.status != 'Booked':
            raise BusinessRuleViolation('INVALID_MODIFY_STATUS', 'Only Booked bookings can be modified')

        if 'startTime' in data:
            booking.start_time = datetime.strptime(data['startTime'], '%H:%M').time()

        if 'therapistId' in data:
            booking.therapist_id = data['therapistId']

        db.session.commit()

        return booking

    @staticmethod
    def cancel(booking_id):
        booking = Booking.query.get(booking_id)
        if not booking:
            raise ResourceNotFound('Booking')

        if booking.status != 'Booked':
            raise BusinessRuleViolation('INVALID_CANCEL_STATUS', 'Only Booked bookings can be cancelled')

        booking.status = 'Cancelled'
        db.session.commit()

        return booking

    @staticmethod
    def checkin(booking_id):
        booking = Booking.query.get(booking_id)
        if not booking:
            raise ResourceNotFound('Booking')

        if booking.status != 'Booked':
            raise BusinessRuleViolation('INVALID_CHECKIN_STATUS', 'Only Booked bookings can be checked in')

        booking.status = 'CheckedIn'
        db.session.commit()

        return booking

    @staticmethod
    def checkout(booking_id):
        booking = Booking.query.get(booking_id)
        if not booking:
            raise ResourceNotFound('Booking')

        if booking.status != 'CheckedIn':
            raise BusinessRuleViolation('INVALID_CHECKOUT_STATUS', 'Only CheckedIn bookings can be checked out')

        booking.status = 'CheckedOut'
        db.session.commit()

        return booking

    @staticmethod
    def _booking_to_dict(booking, detailed=False):
        result = {
            'bookingId': booking.id,
            'bookingCode': booking.booking_code,
            'shopId': booking.shop_id,
            'shopName': booking.shop.name if booking.shop else None,
            'phoneNumber': booking.phone_number,
            'bookingDate': booking.booking_date.strftime('%Y-%m-%d'),
            'startTime': booking.start_time.strftime('%H:%M'),
            'endTime': booking.end_time.strftime('%H:%M'),
            'numberOfPeople': booking.number_of_people,
            'status': booking.status
        }

        if booking.therapist:
            result['therapistId'] = booking.therapist.id
            result['therapistName'] = booking.therapist.name

        if detailed:
            result['services'] = [{
                'personIndex': s.person_index,
                'courseId': s.course_id,
                'courseName': s.course.name if s.course else None
            } for s in booking.services]

            result['addOns'] = [{
                'personIndex': a.person_index,
                'courseId': a.course_id,
                'courseName': a.course.name if a.course else None
            } for a in booking.addons]

            if booking.preferences_json:
                try:
                    result['preferences'] = json.loads(booking.preferences_json)
                except (json.JSONDecodeError, TypeError):
                    result['preferences'] = None

        return result
