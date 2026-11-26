from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from threading import Barrier

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Booking, Course, Shop, Therapist, TherapistShift
from app.models.booking import BookingTherapist


def _date(days=7):
    return (datetime.utcnow().date() + timedelta(days=days)).isoformat()


def _create(client, shop_id, course_id, *, start='10:00', guests=1, phone='0901234567', **extra):
    response = client.post('/api/bookings', json={
        'phoneNumber': phone,
        'shopId': shop_id,
        'bookingDate': _date(),
        'startTime': start,
        'duration': 60,
        'numberOfPeople': guests,
        'courseId': course_id,
        **extra,
    })
    assert response.status_code == 201, response.get_json()
    return response.get_json()['data']['bookingId']


def _snapshot(booking_id):
    db.session.expire_all()
    booking = db.session.get(Booking, booking_id)
    return {
        'date': booking.booking_date,
        'start': booking.start_time,
        'end': booking.end_time,
        'therapist': booking.therapist_id,
        'status': booking.status,
        'preferences': booking.preferences_json,
        'updated': booking.updated_at,
        'services': sorted((s.person_index, s.course_id) for s in booking.services),
        'addons': sorted((a.person_index, a.course_id) for a in booking.addons),
        'assignments': sorted((a.person_index, a.therapist_id) for a in booking.booking_therapists),
    }


def test_start_time_patch_recalculates_end_and_keeps_assignment(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    before = _snapshot(booking_id)
    response = client.patch(f'/api/bookings/{booking_id}', json={'startTime': '11:00'})
    assert response.status_code == 200, response.get_json()
    assert response.get_json() == {
        'success': True, 'data': {'bookingId': booking_id, 'status': 'Booked'},
        'message': 'Booking updated',
    }
    after = _snapshot(booking_id)
    assert after['start'] == time(11, 0)
    assert after['end'] == time(12, 0)
    assert after['therapist'] == before['therapist']
    assert after['assignments'] == before['assignments']


def test_duration_and_course_patch_recalculates_end(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    response = client.patch(f'/api/bookings/{booking_id}', json={
        'duration': 90,
        'services': [
            {'personIndex': 1, 'courseId': sample_courses[0].id},
            {'personIndex': 1, 'courseId': sample_courses[1].id},
        ],
    })
    assert response.status_code == 200, response.get_json()
    after = _snapshot(booking_id)
    assert after['end'] == time(11, 30)
    assert after['services'] == [(1, sample_courses[0].id), (1, sample_courses[1].id)]


def test_date_patch_rechecks_shift_and_shop_hours(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    next_date = _date(8)
    response = client.patch(f'/api/bookings/{booking_id}', json={'bookingDate': next_date})
    assert response.status_code == 200, response.get_json()
    assert _snapshot(booking_id)['date'].isoformat() == next_date

    before = _snapshot(booking_id)
    response = client.patch(f'/api/bookings/{booking_id}', json={'startTime': '20:30'})
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'SHOP_CLOSED'
    assert _snapshot(booking_id) == before


def test_explicit_therapist_change_updates_both_assignment_representations(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    current = _snapshot(booking_id)['therapist']
    target = next(t.id for t in sample_therapists if t.id != current)
    response = client.patch(f'/api/bookings/{booking_id}', json={'therapistId': target})
    assert response.status_code == 200, response.get_json()
    after = _snapshot(booking_id)
    assert after['therapist'] == target
    assert after['assignments'] == [(1, target)]


def test_legacy_pointer_only_booking_gains_consistent_assignment_row(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    booking = db.session.get(Booking, booking_id)
    legacy_therapist = booking.therapist_id
    booking.booking_therapists.clear()
    db.session.commit()

    response = client.patch(f'/api/bookings/{booking_id}', json={'startTime': '11:00'})
    assert response.status_code == 200, response.get_json()
    after = _snapshot(booking_id)
    assert after['therapist'] == legacy_therapist
    assert after['assignments'] == [(1, legacy_therapist)]


def test_group_reschedule_reassigns_distinct_therapists_when_needed(
        client, sample_shop, sample_courses, sample_therapists):
    group_id = _create(client, sample_shop.id, sample_courses[0].id, guests=2)
    old_ids = [therapist_id for _, therapist_id in _snapshot(group_id)['assignments']]
    _create(client, sample_shop.id, sample_courses[0].id, start='11:00',
            phone='0901234568', therapistPreferenceType='specific',
            therapistPreferenceValue=old_ids[0])

    response = client.patch(f'/api/bookings/{group_id}', json={'startTime': '11:00'})
    assert response.status_code == 200, response.get_json()
    after = _snapshot(group_id)
    assigned_ids = [therapist_id for _, therapist_id in after['assignments']]
    assert len(set(assigned_ids)) == 2
    assert old_ids[0] not in assigned_ids
    assert after['therapist'] == assigned_ids[0]
    assert after['end'] == time(12, 0)


def test_group_patch_rejects_insufficient_capacity_without_changes(
        client, sample_shop, sample_courses, sample_therapists):
    group_id = _create(client, sample_shop.id, sample_courses[0].id, guests=2)
    _create(client, sample_shop.id, sample_courses[0].id, start='11:00',
            phone='0901234568')
    _create(client, sample_shop.id, sample_courses[0].id, start='11:00',
            phone='0901234569')
    before = _snapshot(group_id)
    response = client.patch(f'/api/bookings/{group_id}', json={'startTime': '11:00'})
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'INSUFFICIENT_THERAPISTS'
    assert _snapshot(group_id) == before


def test_specific_patch_rechecks_shift_and_gender_preference(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    before = _snapshot(booking_id)
    next_date = date.fromisoformat(_date(8))
    target = next(t for t in sample_therapists if t.id != before['therapist'])
    for shift in TherapistShift.query.filter_by(therapist_id=target.id).all():
        shift.effective_from = next_date + timedelta(days=1)
    db.session.commit()

    response = client.patch(f'/api/bookings/{booking_id}', json={
        'bookingDate': next_date.isoformat(), 'therapistId': target.id,
    })
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'SLOT_UNAVAILABLE'
    assert _snapshot(booking_id) == before

    response = client.patch(f'/api/bookings/{booking_id}', json={
        'therapistPreferenceType': 'gender',
        'therapistPreferenceValue': 'Female',
    })
    assert response.status_code == 200, response.get_json()
    after = _snapshot(booking_id)
    assert db.session.get(Therapist, after['therapist']).gender == 'Female'
    assert after['assignments'] == [(1, after['therapist'])]


def test_selected_course_option_is_revalidated_on_patch(
        client, sample_shop, sample_courses, sample_therapists):
    course = sample_courses[0]
    course.set_durations([
        {'duration': 60, 'price': 6000},
        {'duration': 90, 'price': 9000},
    ])
    db.session.commit()
    booking_id = _create(client, sample_shop.id, course.id)
    before = _snapshot(booking_id)
    response = client.patch(f'/api/bookings/{booking_id}', json={
        'duration': 90,
        'selectedCourses': [{'courseId': course.id, 'duration': 90, 'price': 1}],
    })
    assert response.status_code == 400
    assert response.get_json()['error']['code'] == 'VALIDATION_ERROR'
    assert _snapshot(booking_id) == before

    response = client.patch(f'/api/bookings/{booking_id}', json={
        'duration': 90,
        'selectedCourses': [{'courseId': course.id, 'duration': 90, 'price': 9000}],
    })
    assert response.status_code == 200, response.get_json()
    after = _snapshot(booking_id)
    assert after['end'] == time(11, 30)
    assert '"selectedCourses"' in after['preferences']


def test_rejected_patch_preserves_all_booking_state(
        client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    target = next(t.id for t in sample_therapists
                  if t.id != _snapshot(booking_id)['therapist'])
    _create(client, sample_shop.id, sample_courses[0].id, start='11:00',
            phone='0901234568', therapistPreferenceType='specific',
            therapistPreferenceValue=target)
    before = _snapshot(booking_id)
    for payload, status, code in [
        ({'startTime': '11:00', 'therapistId': target}, 422, 'SLOT_UNAVAILABLE'),
        ({'duration': 90}, 400, 'VALIDATION_ERROR'),
        ({'duration': 10 ** 100}, 400, 'VALIDATION_ERROR'),
        ({'startTime': 'bad'}, 400, 'VALIDATION_ERROR'),
        ({'phoneNumber': '0999999999'}, 400, 'VALIDATION_ERROR'),
    ]:
        response = client.patch(f'/api/bookings/{booking_id}', json=payload)
        assert response.status_code == status, response.get_json()
        assert response.get_json()['error']['code'] == code
        assert _snapshot(booking_id) == before


@pytest.mark.parametrize('status', ['CheckedIn', 'CheckedOut', 'Cancelled'])
def test_only_booked_can_be_modified(
        client, sample_shop, sample_courses, sample_therapists, status):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    booking = db.session.get(Booking, booking_id)
    booking.status = status
    db.session.commit()
    before = _snapshot(booking_id)
    response = client.patch(f'/api/bookings/{booking_id}', json={'startTime': '11:00'})
    assert response.status_code == 422
    assert response.get_json()['error']['code'] == 'INVALID_MODIFY_STATUS'
    assert _snapshot(booking_id) == before


def test_malformed_patch_returns_structured_validation_error(client, sample_shop,
                                                             sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop.id, sample_courses[0].id)
    before = _snapshot(booking_id)
    response = client.patch(f'/api/bookings/{booking_id}', data='{',
                            content_type='application/json')
    assert response.status_code == 400
    assert response.get_json()['error']['code'] == 'VALIDATION_ERROR'
    assert _snapshot(booking_id) == before


def test_concurrent_create_and_modify_cannot_take_same_therapist(tmp_path, monkeypatch):
    database_path = tmp_path / 'booking-update-race.db'
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{database_path}')
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
            therapist_id=therapist.id, day_of_week=date.fromisoformat(_date()).strftime('%A'),
            start_time=time(9, 0), end_time=time(21, 0), effective_from=date(2026, 1, 1),
        ))
        db.session.commit()
        shop_id, course_id = shop.id, course.id
        with app.test_client() as client:
            booking_id = _create(client, shop_id, course_id, start='10:00')

    barrier = Barrier(2)

    def modify():
        with app.test_client() as client:
            barrier.wait(timeout=5)
            response = client.patch(f'/api/bookings/{booking_id}', json={'startTime': '11:00'})
            return response.status_code, response.get_json()

    def create():
        with app.test_client() as client:
            barrier.wait(timeout=5)
            response = client.post('/api/bookings', json={
                'phoneNumber': '0901234568', 'shopId': shop_id,
                'bookingDate': _date(), 'startTime': '11:00',
                'duration': 60, 'courseId': course_id,
            })
            return response.status_code, response.get_json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda operation: operation(), (modify, create)))

    assert sorted(status for status, _ in results) == [200, 422] or sorted(
        status for status, _ in results) == [201, 422]
    with app.app_context():
        overlapping = Booking.query.filter(
            Booking.booking_date == date.fromisoformat(_date()),
            Booking.start_time < time(12, 0), Booking.end_time > time(11, 0),
            Booking.status == 'Booked',
        ).count()
        assert overlapping == 1
        db.session.remove()
        db.drop_all()
