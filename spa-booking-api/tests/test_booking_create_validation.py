from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Booking, Course, Shop


@pytest.fixture
def booking_payload(sample_shop, sample_courses, sample_therapists):
    course = sample_courses[0]
    return {
        'phoneNumber': '0901234567',
        'shopId': sample_shop.id,
        'bookingDate': (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
        'startTime': '10:00',
        'duration': 60,
        'numberOfPeople': 1,
        'services': [{'personIndex': 1, 'courseId': course.id}],
    }


@pytest.mark.parametrize('changes', [
    {'numberOfPeople': 0},
    {'duration': 0},
    {'duration': 30},
    {'numberOfPeople': 2},
    {'services': [{'personIndex': 2, 'courseId': 1}]},
    {'therapistPreferenceType': 'unknown'},
    {'therapistPreferenceType': 'specific', 'therapistPreferenceValue': True},
    {'numberOfPeople': 2, 'therapistPreferenceType': 'specific', 'therapistPreferenceValue': '1'},
    {'numberOfPeople': 2, 'therapistPreferenceType': 'gender', 'therapistPreferenceValue': 'Female'},
])
def test_create_rejects_invalid_booking_data(client, booking_payload, changes):
    response = client.post('/api/bookings', json={**booking_payload, **changes})
    assert response.status_code == 400
    assert response.get_json()['error']['code'] == 'VALIDATION_ERROR'
    assert Booking.query.count() == 0


@pytest.mark.parametrize('start_time,duration', [('07:45', 60), ('20:30', 60)])
def test_create_rejects_time_outside_shop_hours(client, booking_payload, start_time, duration):
    response = client.post('/api/bookings', json={
        **booking_payload, 'startTime': start_time, 'duration': duration,
    })
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'SHOP_CLOSED'


@pytest.mark.parametrize('preference', [
    {},
    {'therapistPreferenceType': 'specific', 'therapistPreferenceValue': '1'},
    {'therapistPreferenceType': 'gender', 'therapistPreferenceValue': 'Female'},
])
def test_create_rejects_therapists_outside_shift(client, booking_payload, sample_therapists, preference):
    if preference.get('therapistPreferenceType') == 'specific':
        preference = {**preference, 'therapistPreferenceValue': str(sample_therapists[0].id)}
    response = client.post('/api/bookings', json={
        **booking_payload, 'startTime': '08:00', **preference,
    })
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'SLOT_UNAVAILABLE'
    assert Booking.query.count() == 0


def test_create_rejects_closed_shop(client, booking_payload, sample_shop):
    sample_shop.status = 'Closed'
    db.session.commit()
    response = client.post('/api/bookings', json=booking_payload)
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'SHOP_CLOSED'


def test_create_rejects_addon_as_main_course(client, booking_payload, sample_courses):
    response = client.post('/api/bookings', json={
        **booking_payload,
        'services': [{'personIndex': 1, 'courseId': sample_courses[2].id}],
    })
    assert response.status_code == 400
    assert Booking.query.count() == 0


def test_create_rejects_course_from_another_shop(client, booking_payload, sample_courses):
    other_shop = Shop(name='Other', address='Elsewhere', phone_number='0123456780',
                      open_time=datetime.strptime('08:00', '%H:%M').time(),
                      close_time=datetime.strptime('21:00', '%H:%M').time())
    db.session.add(other_shop)
    db.session.flush()
    other_course = Course(shop_id=other_shop.id, name='Other massage',
                          duration=60, price=6000, course_type='main')
    db.session.add(other_course)
    db.session.commit()
    response = client.post('/api/bookings', json={
        **booking_payload,
        'services': [{'personIndex': 1, 'courseId': other_course.id}],
    })
    assert response.status_code == 400
    assert Booking.query.count() == 0


def test_create_rejects_stale_catalog_price(client, booking_payload, sample_courses):
    response = client.post('/api/bookings', json={
        **booking_payload,
        'selectedCourses': [{'courseId': sample_courses[0].id, 'duration': 60, 'price': 1}],
    })
    assert response.status_code == 400
    assert Booking.query.count() == 0


def test_create_accepts_legacy_course_id_and_catalog_option(client, booking_payload, sample_courses):
    sample_courses[0].set_durations([
        {'duration': 30, 'price': 3000}, {'duration': 60, 'price': 6000},
    ])
    db.session.commit()
    response = client.post('/api/bookings', json={
        **booking_payload,
        'courseId': sample_courses[0].id,
        'services': [],
    })
    assert response.status_code == 201
    booking = db.session.get(Booking, response.get_json()['data']['bookingId'])
    assert [(service.person_index, service.course_id) for service in booking.services] == [
        (1, sample_courses[0].id),
    ]


def test_create_rejects_inactive_course(client, booking_payload, sample_courses):
    sample_courses[0].status = 'inactive'
    db.session.commit()
    response = client.post('/api/bookings', json=booking_payload)
    assert response.status_code == 400
    assert Booking.query.count() == 0


def test_create_preserves_multi_main_and_addon_contract(client, booking_payload, sample_courses):
    addon = Course(shop_id=booking_payload['shopId'], name='Aroma', duration=15,
                   price=1000, course_type='addon')
    db.session.add(addon)
    db.session.commit()
    main_ids = [sample_courses[0].id, sample_courses[1].id]
    response = client.post('/api/bookings', json={
        **booking_payload,
        'duration': 105,
        'numberOfPeople': 2,
        'services': [{'personIndex': person, 'courseId': course_id}
                     for person in (1, 2) for course_id in main_ids],
        'addOns': [{'personIndex': person, 'courseId': addon.id} for person in (1, 2)],
        'selectedCourses': [
            {'courseId': sample_courses[0].id, 'duration': 60, 'price': 6000},
            {'courseId': sample_courses[1].id, 'duration': 30, 'price': 3000},
            {'courseId': addon.id, 'duration': 15, 'price': 1000},
        ],
    })
    assert response.status_code == 201
    booking = db.session.get(Booking, response.get_json()['data']['bookingId'])
    assert len(booking.services) == 4
    assert len(booking.addons) == 2
    assert len(booking.booking_therapists) == 2
