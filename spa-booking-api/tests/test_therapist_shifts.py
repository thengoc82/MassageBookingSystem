from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Booking, Therapist, TherapistShift


def _headers(role='admin'):
    token = create_access_token(identity={'role': role, 'type': role, 'user_id': 1})
    return {'Authorization': f'Bearer {token}'}


def _therapist(shop):
    therapist = Therapist(shop_id=shop.id, name='Shift Tester', gender='Female', status='active')
    db.session.add(therapist)
    db.session.commit()
    return therapist


def _date(days=7):
    return datetime.utcnow().date() + timedelta(days=days)


def _payload(therapist, day=None, effective=None, start='09:00', end='17:00'):
    return {
        'therapistId': therapist.id,
        'dayOfWeek': day or _date().strftime('%A'),
        'startTime': start,
        'endTime': end,
        'effectiveFrom': (effective or _date()).isoformat(),
    }


def _slot(client, shop, date=None, start='10:00'):
    response = client.get(f'/api/shops/{shop.id}/available-slots', query_string={
        'date': (date or _date()).isoformat(), 'startTime': start,
        'duration': 60, 'numberOfPeople': 1, 'show_therapists': 'true',
    })
    assert response.status_code == 200, response.get_json()
    return next(item for item in response.get_json()['data'] if item['startTime'] == start)


def test_shift_routes_require_admin(client, sample_shop):
    paths = [
        ('get', f'/api/admin/shops/{sample_shop.id}/therapist-shifts'),
        ('post', '/api/admin/therapist-shifts'),
        ('get', '/api/admin/therapist-shifts/1'),
        ('patch', '/api/admin/therapist-shifts/1'),
        ('delete', '/api/admin/therapist-shifts/1'),
    ]
    for method, path in paths:
        assert getattr(client, method)(path).status_code == 401
        assert getattr(client, method)(path, headers=_headers('therapist')).status_code == 403
        assert getattr(client, method)(path, headers=_headers('customer')).status_code == 403


def test_shift_crud_filters_and_booking_schedule_contract(client, sample_shop):
    therapist = _therapist(sample_shop)
    other = _therapist(sample_shop)
    headers = _headers()
    created = client.post('/api/admin/therapist-shifts', json=_payload(therapist), headers=headers)
    assert created.status_code == 201, created.get_json()
    shift_id = created.get_json()['data']['shiftId']
    assert client.post('/api/admin/therapist-shifts', json=_payload(other), headers=headers).status_code == 201

    listed = client.get(f'/api/admin/shops/{sample_shop.id}/therapist-shifts',
                        query_string={'therapistId': therapist.id, 'dayOfWeek': _date().strftime('%A')},
                        headers=headers)
    assert listed.status_code == 200
    assert [item['shiftId'] for item in listed.get_json()['data']] == [shift_id]
    assert client.get(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).get_json()['data']['startTime'] == '09:00'
    updated = client.patch(f'/api/admin/therapist-shifts/{shift_id}', json={'endTime': '18:00'}, headers=headers)
    assert updated.status_code == 200
    assert updated.get_json()['data']['endTime'] == '18:00'
    schedule = client.get(f'/api/admin/therapists/{therapist.id}/schedule',
                          query_string={'dateFrom': _date().isoformat(), 'dateTo': _date().isoformat()},
                          headers=headers)
    assert schedule.status_code == 200
    assert schedule.get_json()['data'] == {'therapistId': therapist.id, 'name': therapist.name, 'schedule': []}
    assert client.delete(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).status_code == 200
    assert client.get(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).status_code == 404
    assert client.get('/api/admin/shops/999999/therapist-shifts', headers=headers).status_code == 404


def test_shift_validation_and_overlap(client, sample_shop):
    therapist = _therapist(sample_shop)
    headers = _headers()
    base = _payload(therapist)
    bad = [
        ({'dayOfWeek': 'Funday'}, 400),
        ({'startTime': '9:00'}, 400),
        ({'endTime': '09:00'}, 400),
        ({'effectiveFrom': '2026-02-29'}, 400),
        ({'therapistId': True}, 400),
    ]
    for change, status in bad:
        assert client.post('/api/admin/therapist-shifts', json={**base, **change}, headers=headers).status_code == status
    assert client.post('/api/admin/therapist-shifts', data='[1]', content_type='application/json', headers=headers).status_code == 400
    assert client.post('/api/admin/therapist-shifts', json={**base, 'therapistId': 999999}, headers=headers).status_code == 404

    created = client.post('/api/admin/therapist-shifts', json=base, headers=headers)
    shift_id = created.get_json()['data']['shiftId']
    overlap = client.post('/api/admin/therapist-shifts',
                          json=_payload(therapist, effective=_date(14), start='16:00', end='19:00'), headers=headers)
    assert overlap.status_code == 409
    assert overlap.get_json()['error']['code'] == 'SHIFT_OVERLAP'
    adjacent = client.post('/api/admin/therapist-shifts',
                           json=_payload(therapist, start='17:00', end='19:00'), headers=headers)
    assert adjacent.status_code == 201
    rejected = client.patch(f'/api/admin/therapist-shifts/{shift_id}', json={'endTime': '17:30'}, headers=headers)
    assert rejected.status_code == 409
    assert client.get(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).get_json()['data']['endTime'] == '17:00'
    assert client.patch(f'/api/admin/therapist-shifts/{shift_id}', json={'therapistId': 999}, headers=headers).status_code == 400
    assert client.get(f'/api/admin/shops/{sample_shop.id}/therapist-shifts',
                      query_string={'dayOfWeek': 'Funday'}, headers=headers).status_code == 400


def test_shift_changes_recalculate_slot_capacity_and_effective_date(client, sample_shop):
    therapist = _therapist(sample_shop)
    headers = _headers()
    assert _slot(client, sample_shop)['availableCapacity'] == 0
    payload = _payload(therapist, effective=_date(14))
    created = client.post('/api/admin/therapist-shifts', json=payload, headers=headers)
    shift_id = created.get_json()['data']['shiftId']
    assert _slot(client, sample_shop)['availableCapacity'] == 0
    assert _slot(client, sample_shop, _date(14))['availableTherapistIds'] == [therapist.id]
    assert client.patch(f'/api/admin/therapist-shifts/{shift_id}',
                        json={'effectiveFrom': _date().isoformat()}, headers=headers).status_code == 200
    assert _slot(client, sample_shop)['availableCapacity'] == 1
    assert client.patch(f'/api/admin/therapist-shifts/{shift_id}',
                        json={'startTime': '11:00'}, headers=headers).status_code == 200
    assert _slot(client, sample_shop)['availableCapacity'] == 0
    assert _slot(client, sample_shop, start='11:00')['availableCapacity'] == 1
    assert client.delete(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).status_code == 200
    assert _slot(client, sample_shop, start='11:00')['availableCapacity'] == 0


def test_edit_or_delete_cannot_uncover_future_booking(client, sample_shop, sample_courses):
    therapist = _therapist(sample_shop)
    headers = _headers()
    created = client.post('/api/admin/therapist-shifts', json=_payload(therapist), headers=headers)
    shift_id = created.get_json()['data']['shiftId']
    booked = client.post('/api/bookings', json={
        'phoneNumber': '0901234567', 'shopId': sample_shop.id,
        'bookingDate': _date().isoformat(), 'startTime': '10:00',
        'duration': 60, 'numberOfPeople': 1, 'courseId': sample_courses[0].id,
        'therapistPreferenceType': 'specific', 'therapistPreferenceValue': therapist.id,
    })
    assert booked.status_code == 201, booked.get_json()
    for change in ({'startTime': '11:00'}, {'effectiveFrom': _date(14).isoformat()},
                   {'dayOfWeek': _date(1).strftime('%A')}):
        rejected = client.patch(f'/api/admin/therapist-shifts/{shift_id}', json=change, headers=headers)
        assert rejected.status_code == 409
        assert rejected.get_json()['error']['code'] == 'SHIFT_BOOKING_CONFLICT'
    rejected = client.delete(f'/api/admin/therapist-shifts/{shift_id}', headers=headers)
    assert rejected.status_code == 409
    # Older rows may have no legacy pointer; per-guest assignments still need coverage.
    booking = db.session.get(Booking, booked.get_json()['data']['bookingId'])
    booking.therapist_id = None
    db.session.commit()
    assert client.delete(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).status_code == 409
    assert _slot(client, sample_shop)['availableCapacity'] == 0  # The therapist is occupied by the booking.
    assert TherapistShift.query.filter_by(id=shift_id).first() is not None
    assert client.get(f'/api/admin/therapists/{therapist.id}/schedule',
                      query_string={'dateFrom': _date().isoformat(), 'dateTo': _date().isoformat()},
                      headers=headers).get_json()['data']['schedule'][0]['bookingId'] == booked.get_json()['data']['bookingId']
    booking.status = 'CheckedIn'
    db.session.commit()
    assert client.delete(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).status_code == 409
    booking.status = 'Cancelled'
    db.session.commit()
    assert client.delete(f'/api/admin/therapist-shifts/{shift_id}', headers=headers).status_code == 200
