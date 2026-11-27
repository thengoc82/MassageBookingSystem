import json
import random
import string
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.booking import Booking, BookingAddon, BookingTherapist
from app.models.booking import BookingService as BookingServiceModel
from app.models.course import Course
from app.models.shop import Shop
from app.services.customer_service import CustomerService
from app.services.therapist_service import TherapistService
from app.utils.errors import APIError, BusinessRuleViolation, Forbidden, ResourceNotFound, ValidationError


class BookingService:
    @staticmethod
    def create(data):
        if not isinstance(data, dict):
            raise ValidationError('A JSON booking object is required')

        phone_number = data.get('phoneNumber')
        if not isinstance(phone_number, str) or not phone_number.strip():
            raise ValidationError('phoneNumber is required')
        phone_number = phone_number.strip()

        shop_id = data.get('shopId')
        booking_date_str = data.get('bookingDate')
        start_time_str = data.get('startTime')
        duration = data.get('duration')
        number_of_people = data.get('numberOfPeople', 1)

        if not all([shop_id, booking_date_str, start_time_str, duration]):
            raise ValidationError('shopId, bookingDate, startTime, and duration are required')
        if type(shop_id) is not int or shop_id <= 0:
            raise ValidationError('shopId must be a positive integer')
        if type(duration) is not int or duration <= 0:
            raise ValidationError('duration must be a positive integer')
        if type(number_of_people) is not int or number_of_people <= 0:
            raise ValidationError('numberOfPeople must be a positive integer')

        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except (TypeError, ValueError):
            raise ValidationError('bookingDate must be YYYY-MM-DD and startTime must be HH:MM')

        if booking_date < datetime.utcnow().date():
            raise ValidationError('bookingDate cannot be in the past')

        start_datetime = datetime.combine(booking_date, start_time)
        end_datetime = start_datetime + timedelta(minutes=duration)
        end_time = end_datetime.time()

        therapist_preference_type = data.get('therapistPreferenceType')
        therapist_preference_value = data.get('therapistPreferenceValue')
        if therapist_preference_type not in (None, 'no_preference', 'specific', 'gender'):
            raise ValidationError('Invalid therapistPreferenceType')
        if number_of_people > 1 and therapist_preference_type in ('specific', 'gender'):
            raise ValidationError('Therapist preferences are only available for one guest')
        if therapist_preference_type == 'specific':
            if (type(therapist_preference_value) not in (int, str)
                    or not str(therapist_preference_value).isdigit()
                    or int(therapist_preference_value) <= 0):
                raise ValidationError('Invalid therapist ID')
        elif therapist_preference_type == 'gender':
            if therapist_preference_value not in ('Male', 'Female'):
                raise ValidationError('Invalid therapist gender')
        elif therapist_preference_value is not None:
            raise ValidationError('therapistPreferenceValue requires a therapist preference')

        try:
            # On SQLite, this acquires the write lock before any database read
            # that affects assignment. A competing create waits and rechecks.
            shop = BookingService._lock_shop_for_booking(shop_id)
            if not shop:
                raise ResourceNotFound('Shop')
            if (shop.status != 'Open' or start_time < shop.open_time
                    or end_datetime.date() != booking_date or end_time > shop.close_time):
                raise BusinessRuleViolation('SHOP_CLOSED', 'Shop is not open for the requested time')

            service_data, addon_data = BookingService._validate_course_selection(
                data, shop_id, number_of_people, duration
            )

            eligibility = CustomerService.check_eligibility(phone_number, lock=True)
            if not eligibility['isEligible']:
                raise BusinessRuleViolation('CUSTOMER_BLOCKED', 'Customer on NG List')

            assigned_therapist = None
            assigned_therapists = []
            available_therapists = TherapistService.find_available_therapists(
                shop_id, booking_date, start_time, end_time
            )

            if number_of_people == 1 and therapist_preference_type == 'specific' and therapist_preference_value:
                therapist_id = int(therapist_preference_value)
                selected_therapists = [
                    t for t in available_therapists if t.id == therapist_id
                ]
                if not selected_therapists:
                    raise BusinessRuleViolation('SLOT_UNAVAILABLE', 'Requested therapist is no longer available at this time')

            elif number_of_people == 1 and therapist_preference_type == 'gender' and therapist_preference_value:
                candidates = [
                    t for t in available_therapists if t.gender == therapist_preference_value
                ]
                if not candidates:
                    raise BusinessRuleViolation('SLOT_UNAVAILABLE', f'No {therapist_preference_value} therapist available at this time')
                selected_therapists = BookingService._rank_by_daily_workload(
                    candidates, booking_date
                )[:1]

            elif number_of_people == 1 and (not therapist_preference_type or therapist_preference_type == 'no_preference'):
                if not available_therapists:
                    raise BusinessRuleViolation('SLOT_UNAVAILABLE', 'No therapist is available at this time')
                selected_therapists = BookingService._rank_by_daily_workload(
                    available_therapists, booking_date
                )[:1]

            else:
                if len(available_therapists) < number_of_people:
                    raise BusinessRuleViolation('INSUFFICIENT_THERAPISTS',
                        f'Need {number_of_people} therapists, only {len(available_therapists)} available')
                selected_therapists = BookingService._rank_by_daily_workload(
                    available_therapists, booking_date
                )[:number_of_people]

            for person_idx, therapist in enumerate(selected_therapists, start=1):
                assigned_therapists.append((person_idx, therapist))
            assigned_therapist = selected_therapists[0]

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

            for person_idx, therapist in assigned_therapists:
                bt = BookingTherapist(
                    booking_id=booking.id,
                    person_index=person_idx,
                    therapist_id=therapist.id
                )
                db.session.add(bt)

            for service in service_data:
                booking_service = BookingServiceModel(
                    booking_id=booking.id,
                    person_index=service['personIndex'],
                    course_id=service['courseId']
                )
                db.session.add(booking_service)

            for addon in addon_data:
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

        except APIError:
            db.session.rollback()
            raise
        except OperationalError as e:
            db.session.rollback()
            if db.engine.dialect.name == 'sqlite' and any(
                marker in str(e.orig).lower() for marker in ('locked', 'busy')
            ):
                raise APIError('BOOKING_CONFLICT', 'Booking capacity is busy; please try again', 409)
            raise BusinessRuleViolation('BOOKING_FAILED', f'Failed to create booking: {str(e)}')
        except Exception as e:
            db.session.rollback()
            raise BusinessRuleViolation('BOOKING_FAILED', f'Failed to create booking: {str(e)}')

    @staticmethod
    def _validate_course_selection(data, shop_id, number_of_people, duration):
        services = data.get('services')
        if not services:
            course_id = data.get('courseId')
            if type(course_id) is not int or course_id <= 0:
                raise ValidationError('courseId or services is required')
            services = [{'personIndex': i, 'courseId': course_id} for i in range(1, number_of_people + 1)]
        addons = data.get('addOns') or []
        if not isinstance(services, list) or not isinstance(addons, list):
            raise ValidationError('services and addOns must be arrays')

        per_person = {i: {'main': [], 'addon': []} for i in range(1, number_of_people + 1)}
        for items, kind in ((services, 'main'), (addons, 'addon')):
            for item in items:
                if not isinstance(item, dict) or type(item.get('personIndex')) is not int or type(item.get('courseId')) is not int:
                    raise ValidationError('Each selected course needs integer personIndex and courseId')
                person_index, course_id = item['personIndex'], item['courseId']
                if person_index not in per_person or course_id <= 0:
                    raise ValidationError('Selected course has an invalid personIndex or courseId')
                if course_id in per_person[person_index][kind]:
                    raise ValidationError('A course cannot be selected twice for one guest')
                per_person[person_index][kind].append(course_id)

        first = per_person[1]
        if not first['main']:
            raise ValidationError('Each guest needs at least one main course')
        if any(selection != first for selection in per_person.values()):
            raise ValidationError('Each guest must have the same courses and add-ons')

        selected_options = data.get('selectedCourses')
        if selected_options is not None and not isinstance(selected_options, list):
            raise ValidationError('selectedCourses must be an array')
        options_by_id = {}
        for option in selected_options or []:
            if not isinstance(option, dict) or type(option.get('courseId')) is not int or type(option.get('duration')) is not int or type(option.get('price')) is not int:
                raise ValidationError('selectedCourses needs integer courseId, duration, and price')
            course_id = option['courseId']
            if course_id in options_by_id or option['duration'] <= 0 or option['price'] < 0:
                raise ValidationError('Invalid selectedCourses option')
            options_by_id[course_id] = option

        selected_ids = first['main'] + first['addon']
        if set(options_by_id) - set(selected_ids):
            raise ValidationError('selectedCourses contains a course not selected for booking')

        total_duration = 0
        for kind in ('main', 'addon'):
            for course_id in first[kind]:
                course = db.session.get(Course, course_id)
                if not course:
                    raise ResourceNotFound('Course')
                if course.shop_id != shop_id or course.course_type != kind or course.status != 'active':
                    raise ValidationError('Selected course is unavailable at this shop or has the wrong type')
                catalog_options = course.get_bookable_durations()
                chosen = options_by_id.get(course_id)
                if chosen:
                    if not any(option['duration'] == chosen['duration'] and option['price'] == chosen['price'] for option in catalog_options):
                        raise ValidationError('Selected course duration or price is no longer available')
                    selected_duration = chosen['duration']
                elif len(catalog_options) == 1:
                    selected_duration = catalog_options[0]['duration']
                elif len(selected_ids) == 1 and any(option['duration'] == duration for option in catalog_options):
                    selected_duration = duration
                else:
                    raise ValidationError('selectedCourses is required to identify course durations')
                total_duration += selected_duration

        if total_duration != duration:
            raise ValidationError('Selected course durations must equal the reserved duration')
        return services, addons

    @staticmethod
    def _lock_shop_for_booking(shop_id):
        if db.engine.dialect.name == 'sqlite':
            db.session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            return db.session.get(Shop, shop_id)
        # All create requests for a shop use the same row as their lock.
        return Shop.query.filter_by(id=shop_id).with_for_update().first()

    @staticmethod
    def _rank_by_daily_workload(therapists, date, exclude_booking_id=None):
        workload = {therapist.id: 0 for therapist in therapists}
        query = db.session.query(Booking).options(
            selectinload(Booking.booking_therapists)
        ).filter(
            Booking.shop_id == therapists[0].shop_id,
            Booking.booking_date == date,
            Booking.status.in_(['Booked', 'CheckedIn']),
        )
        if exclude_booking_id is not None:
            query = query.filter(Booking.id != exclude_booking_id)
        bookings = query.all()
        for booking in bookings:
            minutes = max(0, int((
                datetime.combine(date, booking.end_time)
                - datetime.combine(date, booking.start_time)
            ).total_seconds() // 60))
            assigned_ids = {bt.therapist_id for bt in booking.booking_therapists}
            if booking.therapist_id:
                assigned_ids.add(booking.therapist_id)
            for therapist_id in assigned_ids & workload.keys():
                workload[therapist_id] += minutes
        return sorted(therapists, key=lambda therapist: (workload[therapist.id], therapist.id))

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
            from app.services.booking_access import phone_aliases
            query = query.filter(Booking.phone_number.in_(phone_aliases(filters['phone'])))

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

        query = query.order_by(Booking.created_at.desc().nullslast())
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
        if not isinstance(data, dict) or not data:
            raise ValidationError('A nonempty JSON booking update is required')
        allowed = {
            'bookingDate', 'startTime', 'duration', 'courseId', 'services',
            'addOns', 'selectedCourses', 'therapistId',
            'therapistPreferenceType', 'therapistPreferenceValue',
        }
        if set(data) - allowed:
            raise ValidationError('Booking update contains unsupported fields')

        try:
            # Use the same shop lock as creation. SQLite must lock before the
            # first read; on other databases the shop and booking rows are locked.
            if db.engine.dialect.name == 'sqlite':
                db.session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                booking = db.session.get(Booking, booking_id)
                shop = db.session.get(Shop, booking.shop_id) if booking else None
            else:
                shop_id = db.session.query(Booking.shop_id).filter_by(id=booking_id).scalar()
                shop = BookingService._lock_shop_for_booking(shop_id) if shop_id else None
                booking = (Booking.query.filter_by(id=booking_id)
                           .with_for_update().populate_existing().first()) if shop else None
            if not booking:
                raise ResourceNotFound('Booking')
            if booking.status != 'Booked':
                raise BusinessRuleViolation('INVALID_MODIFY_STATUS', 'Only Booked bookings can be modified')

            try:
                booking_date = (datetime.strptime(data['bookingDate'], '%Y-%m-%d').date()
                                if 'bookingDate' in data else booking.booking_date)
                start_time = (datetime.strptime(data['startTime'], '%H:%M').time()
                              if 'startTime' in data else booking.start_time)
            except (TypeError, ValueError):
                raise ValidationError('bookingDate must be YYYY-MM-DD and startTime must be HH:MM')
            if booking_date < datetime.utcnow().date():
                raise ValidationError('bookingDate cannot be in the past')

            saved_duration = int((
                datetime.combine(booking.booking_date, booking.end_time)
                - datetime.combine(booking.booking_date, booking.start_time)
            ).total_seconds() // 60)
            duration = data.get('duration', saved_duration)
            if type(duration) is not int or duration <= 0:
                raise ValidationError('duration must be a positive integer')
            try:
                end_datetime = datetime.combine(booking_date, start_time) + timedelta(minutes=duration)
            except OverflowError:
                raise ValidationError('duration or bookingDate is out of range')
            end_time = end_datetime.time()
            if (not shop or shop.status != 'Open' or start_time < shop.open_time
                    or end_datetime.date() != booking_date or end_time > shop.close_time):
                raise BusinessRuleViolation('SHOP_CLOSED', 'Shop is not open for the requested time')

            try:
                preferences = json.loads(booking.preferences_json) if booking.preferences_json else {}
            except (TypeError, json.JSONDecodeError):
                preferences = {}
            if not isinstance(preferences, dict):
                preferences = {}
            services = ([{'personIndex': s.person_index, 'courseId': s.course_id}
                         for s in sorted(booking.services, key=lambda item: item.id)])
            addons = ([{'personIndex': a.person_index, 'courseId': a.course_id}
                       for a in sorted(booking.addons, key=lambda item: item.id)])
            selection = {
                'services': data.get('services', services),
                'addOns': data.get('addOns', addons),
            }
            if 'courseId' in data and 'services' not in data:
                selection['services'] = None
                selection['courseId'] = data['courseId']
            if 'selectedCourses' in data:
                selection['selectedCourses'] = data['selectedCourses']
            elif 'selectedCourses' in preferences:
                # Keep saved options for retained courses, not removed ones.
                selected_ids = {item.get('courseId') for items in
                                (selection['services'] or [], selection['addOns'] or [])
                                for item in items if isinstance(item, dict)}
                saved_options = preferences['selectedCourses']
                if isinstance(saved_options, list):
                    selection['selectedCourses'] = [option for option in saved_options
                        if isinstance(option, dict) and option.get('courseId') in selected_ids]
            service_data, addon_data = BookingService._validate_course_selection(
                selection, booking.shop_id, booking.number_of_people, duration
            )

            preference_type = data.get('therapistPreferenceType')
            preference_value = data.get('therapistPreferenceValue')
            if 'therapistId' in data:
                if 'therapistPreferenceType' in data or 'therapistPreferenceValue' in data:
                    raise ValidationError('Use either therapistId or therapist preference fields')
                preference_type = 'specific' if data['therapistId'] is not None else 'no_preference'
                preference_value = data['therapistId']
            if preference_type not in (None, 'specific', 'gender', 'no_preference'):
                raise ValidationError('Invalid therapistPreferenceType')
            if booking.number_of_people > 1 and preference_type in ('specific', 'gender'):
                raise ValidationError('Therapist preferences are only available for one guest')
            if preference_type == 'specific':
                if (type(preference_value) not in (int, str)
                        or not str(preference_value).isdigit() or int(preference_value) <= 0):
                    raise ValidationError('Invalid therapist ID')
                preference_value = int(preference_value)
            elif preference_type == 'gender':
                if preference_value not in ('Male', 'Female'):
                    raise ValidationError('Invalid therapist gender')
            elif preference_value is not None:
                raise ValidationError('therapistPreferenceValue requires a therapist preference')

            available = TherapistService.find_available_therapists(
                booking.shop_id, booking_date, start_time, end_time,
                exclude_booking_id=booking.id,
            )
            available_by_id = {therapist.id: therapist for therapist in available}
            if preference_type == 'specific':
                chosen = [available_by_id[preference_value]] if preference_value in available_by_id else []
            elif preference_type == 'gender':
                candidates = [t for t in available if t.gender == preference_value]
                chosen = (BookingService._rank_by_daily_workload(
                    candidates, booking_date, booking.id)[:1] if candidates else [])
            else:
                # Keep valid assignments stable. Replacements use Task 2's
                # distinct, least-loaded ordering.
                assigned_ids = [bt.therapist_id for bt in
                                sorted(booking.booking_therapists, key=lambda bt: bt.person_index)]
                if not assigned_ids and booking.number_of_people == 1 and booking.therapist_id:
                    assigned_ids = [booking.therapist_id]
                if (len(assigned_ids) == booking.number_of_people
                        and len(set(assigned_ids)) == booking.number_of_people
                        and all(tid in available_by_id for tid in assigned_ids)):
                    chosen = [available_by_id[tid] for tid in assigned_ids]
                else:
                    chosen = (BookingService._rank_by_daily_workload(
                        available, booking_date, booking.id)[:booking.number_of_people]
                        if available else [])
            if len(chosen) < booking.number_of_people:
                if booking.number_of_people > 1:
                    raise BusinessRuleViolation('INSUFFICIENT_THERAPISTS',
                        f'Need {booking.number_of_people} therapists, only {len(available)} available')
                raise BusinessRuleViolation('SLOT_UNAVAILABLE',
                    'Requested therapist is no longer available at this time')

            booking.booking_date = booking_date
            booking.start_time = start_time
            booking.end_time = end_time
            booking.therapist_id = chosen[0].id
            if 'services' in data or 'courseId' in data:
                booking.services = [BookingServiceModel(person_index=s['personIndex'], course_id=s['courseId'])
                                    for s in service_data]
            if 'addOns' in data:
                booking.addons = [BookingAddon(person_index=a['personIndex'], course_id=a['courseId'])
                                  for a in addon_data]
            existing_assignments = {bt.person_index: bt for bt in booking.booking_therapists}
            for person_index, therapist in enumerate(chosen, start=1):
                assignment = existing_assignments.pop(person_index, None)
                if assignment:
                    assignment.therapist_id = therapist.id
                else:
                    booking.booking_therapists.append(BookingTherapist(
                        person_index=person_index, therapist_id=therapist.id
                    ))
            for assignment in existing_assignments.values():
                booking.booking_therapists.remove(assignment)
            if 'selectedCourses' in data or 'services' in data or 'courseId' in data or 'addOns' in data:
                if 'selectedCourses' in selection:
                    preferences['selectedCourses'] = selection['selectedCourses']
                else:
                    preferences.pop('selectedCourses', None)
                booking.preferences_json = json.dumps(preferences, ensure_ascii=False) if preferences else None

            db.session.commit()
            return booking
        except APIError:
            db.session.rollback()
            raise
        except OperationalError as error:
            db.session.rollback()
            if db.engine.dialect.name == 'sqlite' and any(
                marker in str(error.orig).lower() for marker in ('locked', 'busy')
            ):
                raise APIError('BOOKING_CONFLICT', 'Booking capacity is busy; please try again', 409)
            raise
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def cancel(booking_id):
        return BookingService._transition(booking_id, 'Booked', 'Cancelled', 'INVALID_CANCEL_STATUS', 'Only Booked bookings can be cancelled')

    @staticmethod
    def checkin(booking_id, therapist_id=None):
        return BookingService._transition(booking_id, 'Booked', 'CheckedIn', 'INVALID_CHECKIN_STATUS', 'Only Booked bookings can be checked in', therapist_id)

    @staticmethod
    def checkout(booking_id, therapist_id=None):
        return BookingService._transition(booking_id, 'CheckedIn', 'CheckedOut', 'INVALID_CHECKOUT_STATUS', 'Only CheckedIn bookings can be checked out', therapist_id)

    @staticmethod
    def _transition(booking_id, expected, target, error_code, message, therapist_id=None):
        query = Booking.query.filter_by(id=booking_id, status=expected)
        if therapist_id is not None:
            query = query.filter(or_(
                Booking.therapist_id == therapist_id,
                Booking.booking_therapists.any(BookingTherapist.therapist_id == therapist_id),
            ))
        changed = query.update(
            {'status': target}, synchronize_session=False
        )
        if not changed:
            db.session.rollback()
            current = db.session.get(Booking, booking_id)
            if current is None:
                raise ResourceNotFound('Booking')
            if therapist_id is not None and not (
                current.therapist_id == therapist_id or any(
                    row.therapist_id == therapist_id for row in current.booking_therapists
                )
            ):
                raise Forbidden('This booking is not assigned to you')
            raise BusinessRuleViolation(error_code, message)
        db.session.commit()
        return db.session.get(Booking, booking_id)

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

        therapist_assignments = []
        for bt in booking.booking_therapists:
            therapist_assignments.append({
                'personIndex': bt.person_index,
                'therapistId': bt.therapist.id,
                'therapistName': bt.therapist.name,
            })
        if therapist_assignments:
            result['therapistAssignments'] = therapist_assignments

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
