from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from threading import Barrier

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Booking, Course, Customer, Shop, Therapist, TherapistShift
from app.models.booking import BookingTherapist


def _booking_date():
    return datetime.utcnow().date() + timedelta(days=7)


def _payload(shop_id, course_id, guests=1):
    return {
        'phoneNumber': '0901234567',
        'shopId': shop_id,
        'bookingDate': _booking_date().isoformat(),
        'startTime': '10:00',
        'duration': 60,
        'numberOfPeople': guests,
        'courseId': course_id,
    }


def _slot(client, shop_id, start_time='10:00'):
    response = client.get(f'/api/shops/{shop_id}/available-slots', query_string={
        'date': _booking_date().isoformat(),
        'startTime': start_time,
        'duration': 60,
        'numberOfPeople': 1,
        'show_therapists': 'true',
    })
    assert response.status_code == 200
    return next(slot for slot in response.get_json()['data']
                if slot['startTime'] == start_time)


def _seed_booking(shop, customer, therapist_ids, code, status='Booked'):
    booking = Booking(
        booking_code=code,
        shop_id=shop.id,
        customer_id=customer.id,
        phone_number=customer.phone_number,
        booking_date=_booking_date(),
        start_time=time(9, 0),
        end_time=time(10, 0),
        number_of_people=len(therapist_ids),
        therapist_id=therapist_ids[0],
        status=status,
    )
    db.session.add(booking)
    db.session.flush()
    for person_index, therapist_id in enumerate(therapist_ids, start=1):
        db.session.add(BookingTherapist(
            booking_id=booking.id,
            person_index=person_index,
            therapist_id=therapist_id,
        ))
    db.session.commit()
    return booking


def test_group_booking_consumes_one_capacity_per_guest(
        client, sample_shop, sample_courses, sample_therapists):
    assert _slot(client, sample_shop.id)['availableCapacity'] == 3

    response = client.post('/api/bookings', json=_payload(
        sample_shop.id, sample_courses[0].id, guests=2
    ))
    assert response.status_code == 201
    assignments = response.get_json()['data']['therapistAssignments']
    assert [assignment['personIndex'] for assignment in assignments] == [1, 2]
    assigned_ids = {assignment['therapistId'] for assignment in assignments}
    assert len(assigned_ids) == 2

    slot = _slot(client, sample_shop.id)
    assert slot['availableCapacity'] == 1
    assert len(slot['availableTherapistIds']) == 1
    assert assigned_ids.isdisjoint(slot['availableTherapistIds'])

    group_response = client.post('/api/bookings', json={
        **_payload(sample_shop.id, sample_courses[0].id, guests=2),
        'phoneNumber': '0901234568',
    })
    assert group_response.status_code == 422
    assert group_response.get_json()['error']['code'] == 'INSUFFICIENT_THERAPISTS'

    booking_id = response.get_json()['data']['bookingId']
    cancelled = client.patch(f'/api/bookings/{booking_id}/cancel')
    assert cancelled.status_code == 200
    assert _slot(client, sample_shop.id)['availableCapacity'] == 3


def test_capacity_deduplicates_shifts_and_legacy_assignment(
        client, sample_shop, sample_customer, sample_therapists):
    first = sample_therapists[0]
    db.session.add(TherapistShift(
        therapist_id=first.id,
        day_of_week=_booking_date().strftime('%A'),
        start_time=time(9, 0),
        end_time=time(21, 0),
        effective_from=date(2026, 1, 1),
    ))
    db.session.commit()
    assert _slot(client, sample_shop.id)['availableCapacity'] == 3

    booking = Booking(
        booking_code='LEGACY-1',
        shop_id=sample_shop.id,
        customer_id=sample_customer.id,
        phone_number=sample_customer.phone_number,
        booking_date=_booking_date(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        number_of_people=1,
        therapist_id=first.id,
        status='Booked',
    )
    db.session.add(booking)
    db.session.commit()
    assert _slot(client, sample_shop.id)['availableCapacity'] == 2

    db.session.add(BookingTherapist(
        booking_id=booking.id, person_index=1, therapist_id=first.id
    ))
    db.session.commit()
    slot = _slot(client, sample_shop.id)
    assert slot['availableCapacity'] == 2
    assert first.id not in slot['availableTherapistIds']
    assert len(slot['availableTherapistIds']) == slot['availableCapacity']
    assert _slot(client, sample_shop.id, '11:00')['availableCapacity'] == 3


def test_group_assignment_uses_workload_from_every_assignment(
        client, sample_shop, sample_customer, sample_courses, sample_therapists):
    _seed_booking(sample_shop, sample_customer,
                  [sample_therapists[0].id, sample_therapists[1].id], 'GROUP-PAST')

    response = client.post('/api/bookings', json=_payload(
        sample_shop.id, sample_courses[0].id, guests=2
    ))
    assert response.status_code == 201
    assigned_ids = [assignment['therapistId'] for assignment
                    in response.get_json()['data']['therapistAssignments']]
    assert assigned_ids == [sample_therapists[2].id, sample_therapists[0].id]


def test_specific_and_gender_preferences_use_current_capacity(
        client, sample_shop, sample_courses, sample_therapists):
    male_id = sample_therapists[1].id
    specific = client.post('/api/bookings', json={
        **_payload(sample_shop.id, sample_courses[0].id),
        'therapistPreferenceType': 'specific',
        'therapistPreferenceValue': male_id,
    })
    assert specific.status_code == 201
    assert specific.get_json()['data']['therapistId'] == male_id

    unavailable = client.post('/api/bookings', json={
        **_payload(sample_shop.id, sample_courses[0].id),
        'phoneNumber': '0901234568',
        'therapistPreferenceType': 'gender',
        'therapistPreferenceValue': 'Male',
    })
    assert unavailable.status_code == 422
    assert unavailable.get_json()['error']['code'] == 'SLOT_UNAVAILABLE'

    female = client.post('/api/bookings', json={
        **_payload(sample_shop.id, sample_courses[0].id),
        'phoneNumber': '0901234569',
        'therapistPreferenceType': 'gender',
        'therapistPreferenceValue': 'Female',
    })
    assert female.status_code == 201
    assert female.get_json()['data']['therapistId'] == sample_therapists[0].id


def test_occupied_and_terminal_statuses_affect_slots(
        client, sample_shop, sample_customer, sample_therapists):
    first, second, third = sample_therapists
    bookings = []
    for therapist, status in ((first, 'Booked'), (second, 'CheckedIn'),
                              (third, 'Cancelled')):
        booking = Booking(
            booking_code=f'STATUS-{therapist.id}',
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            phone_number=sample_customer.phone_number,
            booking_date=_booking_date(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            number_of_people=1,
            therapist_id=therapist.id,
            status=status,
        )
        db.session.add(booking)
        bookings.append(booking)
    db.session.commit()

    slot = _slot(client, sample_shop.id)
    assert slot['availableCapacity'] == 1
    assert slot['availableTherapistIds'] == [third.id]
    assert _slot(client, sample_shop.id, '11:00')['availableCapacity'] == 3

    bookings[0].status = 'CheckedOut'
    db.session.commit()
    assert _slot(client, sample_shop.id)['availableTherapistIds'] == [first.id, third.id]


def test_concurrent_requests_cannot_book_the_final_therapist(tmp_path, monkeypatch):
    database_path = tmp_path / 'booking-race.db'
    monkeypatch.setattr(
        TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{database_path}'
    )
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        shop = Shop(name='Race Spa', address='Test', phone_number='0123456790',
                    status='Open', open_time=time(8, 0), close_time=time(21, 0))
        db.session.add(shop)
        db.session.flush()
        course = Course(shop_id=shop.id, name='Massage', duration=60,
                        price=6000, course_type='main')
        therapist = Therapist(shop_id=shop.id, name='Only Therapist',
                              gender='Female', status='active')
        db.session.add_all([course, therapist])
        db.session.flush()
        db.session.add(TherapistShift(
            therapist_id=therapist.id,
            day_of_week=_booking_date().strftime('%A'),
            start_time=time(9, 0), end_time=time(21, 0),
            effective_from=date(2026, 1, 1),
        ))
        db.session.commit()
        shop_id, course_id, therapist_id = shop.id, course.id, therapist.id

    barrier = Barrier(2)

    def submit(phone_number):
        with app.test_client() as client:
            barrier.wait(timeout=5)
            response = client.post('/api/bookings', json={
                **_payload(shop_id, course_id), 'phoneNumber': phone_number,
            })
            return response.status_code, response.get_json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, ('0901111111', '0902222222')))

    assert sorted(status for status, _ in results) == [201, 422]
    assert next(body for status, body in results if status == 422)['error']['code'] == 'SLOT_UNAVAILABLE'
    with app.app_context():
        assert Booking.query.count() == 1
        assignments = BookingTherapist.query.all()
        assert len(assignments) == 1
        assert assignments[0].therapist_id == therapist_id
        db.session.remove()
        db.drop_all()
