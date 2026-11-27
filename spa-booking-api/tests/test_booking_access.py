from datetime import datetime, timedelta
import re

import pytest
from flask_jwt_extended import create_access_token

from app.models import Customer
from app import create_app
from app.config import ProductionConfig
from app.services import booking_access
from app.extensions import db


def _token(role, **claims):
    return create_access_token(identity={'role': role, 'type': 'customer_access' if role == 'customer' else role, **claims})


def _headers(token):
    return {'Authorization': f'Bearer {token}'}


def _create(client, shop, course, phone='0901234567', guests=1):
    response = client.post('/api/bookings', json={
        'phoneNumber': phone, 'shopId': shop.id,
        'bookingDate': (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
        'startTime': '10:00', 'duration': 60,
        'numberOfPeople': guests, 'courseId': course.id,
    })
    assert response.status_code == 201, response.get_json()
    return response.get_json()['data']['bookingId']


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def hset(self, key, mapping):
        self.values[key] = dict(mapping)

    def delete(self, key):
        self.values.pop(key, None)

    def eval(self, script, count, key, digest):
        saved = self.values.get(key)
        if not saved:
            return 0
        saved['attempts'] += 1
        if saved['attempts'] > 5:
            self.delete(key)
            return 0
        if saved['digest'] == digest:
            self.delete(key)
            return 1
        return 0


def test_phone_verification_is_one_time_and_rate_limited(client, monkeypatch):
    redis = FakeRedis()
    sent = []
    monkeypatch.setattr(booking_access, '_redis', lambda: redis)
    def fake_delivery(phone, code):
        sent.append((phone, code))
        return 'fake'
    monkeypatch.setattr(booking_access, '_deliver_code', fake_delivery)

    assert client.post('/api/booking-access/challenges', json={'phoneNumber': '+84901234567'}).status_code == 200
    assert sent[0][0] == '0901234567'
    challenge_key = next(key for key in redis.values if key.startswith('booking-access:code:'))
    assert redis.expirations[challenge_key] == 300
    assert redis.values[challenge_key]['digest'] != sent[0][1]
    wrong = client.post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': '999999' if sent[0][1] != '999999' else '999998'})
    assert wrong.status_code == 401
    verified = client.post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': sent[0][1]})
    assert verified.status_code == 200
    assert verified.headers['Cache-Control'] == 'no-store'
    assert verified.get_json()['data']['accessToken']
    assert client.post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': sent[0][1]}).status_code == 401
    for _ in range(2):
        assert client.post('/api/booking-access/challenges', json={'phoneNumber': '0901234567'}).status_code == 200
    assert client.post('/api/booking-access/challenges', json={'phoneNumber': '0901234567'}).status_code == 429


def test_production_rejects_weak_signing_secrets(monkeypatch):
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', 'short')
    monkeypatch.setattr(ProductionConfig, 'JWT_SECRET_KEY', 'short')
    with pytest.raises(RuntimeError):
        create_app('production')


def test_failed_delivery_does_not_leave_a_valid_challenge(client, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(booking_access, '_redis', lambda: redis)
    def delivery_offline(phone, code):
        raise RuntimeError('Delivery offline')
    monkeypatch.setattr(booking_access, '_deliver_code', delivery_offline)
    response = client.post('/api/booking-access/challenges', json={'phoneNumber': '0901234567'})
    assert response.status_code == 503
    assert not any(key.startswith('booking-access:code:') for key in redis.values)
    assert client.post('/api/booking-access/challenges', json={'phoneNumber': 'not-a-phone'}).status_code == 400


def test_development_terminal_delivery_stores_only_hash_and_expires(monkeypatch, capsys):
    redis = FakeRedis()
    monkeypatch.setattr(booking_access, '_redis', lambda: redis)
    app = create_app('development')
    response = app.test_client().post('/api/booking-access/challenges', json={'phoneNumber': '0901234567'})
    assert response.status_code == 200
    assert response.get_json()['data'] == {'delivery': 'terminal'}
    assert '0901234567' not in response.get_data(as_text=True)
    printed = capsys.readouterr().out
    match = re.fullmatch(r'Booking access code for 0901234567: (\d{6}) \(expires in 5 minutes\)\n', printed)
    assert match
    code = match.group(1)
    key = next(key for key in redis.values if key.startswith('booking-access:code:'))
    assert set(redis.values[key]) == {'digest', 'attempts'}
    assert redis.values[key]['digest'] != code
    assert redis.expirations[key] == 300
    verified = app.test_client().post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': code})
    assert verified.status_code == 200
    assert app.test_client().post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': code}).status_code == 401


def test_attempt_limit_and_expired_code(client, monkeypatch):
    redis = FakeRedis()
    delivered = []
    monkeypatch.setattr(booking_access, '_redis', lambda: redis)
    def deliver(phone, code):
        delivered.append((phone, code))
        return 'fake'
    monkeypatch.setattr(booking_access, '_deliver_code', deliver)
    assert client.post('/api/booking-access/challenges', json={'phoneNumber': '0901234567'}).status_code == 200
    code = delivered[-1][1]
    wrong = '999999' if code != '999999' else '999998'
    for _ in range(5):
        assert client.post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': wrong}).status_code == 401
    assert client.post('/api/booking-access/verifications', json={'phoneNumber': '0901234567', 'code': code}).status_code == 401

    assert client.post('/api/booking-access/challenges', json={'phoneNumber': '0901234568'}).status_code == 200
    expiring_key = next(key for key in redis.values if key.startswith('booking-access:code:'))
    redis.delete(expiring_key)
    assert client.post('/api/booking-access/verifications', json={'phoneNumber': '0901234568', 'code': delivered[-1][1]}).status_code == 401


def test_challenge_ip_rate_limit(client, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(booking_access, '_redis', lambda: redis)
    monkeypatch.setattr(booking_access, '_deliver_code', lambda phone, code: 'fake')
    for number in range(20):
        phone = f'090123{number:04d}'
        assert client.post('/api/booking-access/challenges', json={'phoneNumber': phone}).status_code == 200
    assert client.post('/api/booking-access/challenges', json={'phoneNumber': '0901240000'}).status_code == 429


def test_production_never_prints_terminal_code(monkeypatch, capsys):
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', 's' * 32)
    monkeypatch.setattr(ProductionConfig, 'JWT_SECRET_KEY', 'j' * 32)
    monkeypatch.setattr(ProductionConfig, 'BOOKING_ACCESS_DELIVERY_PROVIDER', 'terminal')
    monkeypatch.setattr(booking_access, '_redis', lambda: FakeRedis())
    app = create_app('production')
    response = app.test_client().post('/api/booking-access/challenges', json={'phoneNumber': '0901234567'})
    assert response.status_code == 503
    assert capsys.readouterr().out == ''


def test_customer_scope_and_staff_transitions(client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop, sample_courses[0])
    other_id = _create(client, sample_shop, sample_courses[0], phone='0901234568')
    customer = _headers(_token('customer', phone='0901234567'))
    other_customer = _headers(_token('customer', phone='0901234568'))
    admin = _headers(_token('admin', user_id=1))
    therapist = _headers(_token('therapist', user_id=sample_therapists[0].id))

    assert client.get('/api/bookings').status_code == 400
    assert client.get('/api/bookings?phone=0901234567').status_code == 401
    expired = create_access_token(identity={'role': 'customer', 'type': 'customer_access', 'phone': '0901234567'}, expires_delta=timedelta(seconds=-1))
    assert client.get('/api/bookings?phone=0901234567', headers=_headers(expired)).status_code == 401
    assert client.get('/api/bookings/all').status_code == 404
    assert client.get('/api/bookings?phone=0901234568', headers=customer).status_code == 403
    listing = client.get('/api/bookings?phone=+84901234567', headers=customer)
    assert listing.status_code == 200
    assert listing.headers['Cache-Control'] == 'no-store'
    assert [row['bookingId'] for row in listing.get_json()['data']['data']] == [booking_id]
    assert client.get(f'/api/bookings/{booking_id}').status_code == 401
    assert client.get(f'/api/bookings/{booking_id}', headers=other_customer).status_code == 404
    assert client.patch(f'/api/bookings/{booking_id}', json={'startTime': '11:00'}, headers=other_customer).status_code == 404
    assert client.patch(f'/api/bookings/{booking_id}/cancel', headers=other_customer).status_code == 404
    assert client.patch(f'/api/bookings/{booking_id}/checkin', headers=customer).status_code == 403
    assert client.patch(f'/api/bookings/{booking_id}/checkin', headers=therapist).status_code == 403
    assert client.patch(f'/api/bookings/{booking_id}/checkout', headers=customer).status_code == 403
    assert client.patch(f'/api/bookings/{booking_id}/checkin').status_code == 401
    assert client.get(f'/api/bookings/{booking_id}', headers=admin).status_code == 200
    assert client.patch(f'/api/bookings/{booking_id}', json={'startTime': '11:00'}, headers=customer).status_code == 200
    assert client.patch(f'/api/bookings/{booking_id}/cancel', headers=customer).status_code == 200
    assert client.patch(f'/api/bookings/{other_id}/checkin', headers=admin).status_code == 200
    assert client.patch(f'/api/bookings/{other_id}/checkout', headers=admin).status_code == 200
    assert client.get('/api/admin/bookings', headers=customer).status_code == 403


def test_verified_customer_edit_and_cancel_preserve_booking_on_rejection(
        client, sample_shop, sample_courses, sample_therapists, monkeypatch):
    redis = FakeRedis()
    delivered = []
    monkeypatch.setattr(booking_access, '_redis', lambda: redis)
    monkeypatch.setattr(booking_access, '_deliver_code', lambda phone, code: delivered.append(code) or 'fake')
    booking_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    created = client.post('/api/bookings', json={
        'phoneNumber': '0901234567', 'shopId': sample_shop.id,
        'bookingDate': booking_date, 'startTime': '10:00', 'duration': 60,
        'numberOfPeople': 1, 'courseId': sample_courses[0].id,
        'notes': 'Keep this request',
    })
    assert created.status_code == 201, created.get_json()
    booking_id = created.get_json()['data']['bookingId']
    occupied = client.post('/api/bookings', json={
        'phoneNumber': '0901234568', 'shopId': sample_shop.id,
        'bookingDate': booking_date, 'startTime': '11:00', 'duration': 60,
        'numberOfPeople': 1, 'courseId': sample_courses[0].id,
        'therapistPreferenceType': 'specific',
        'therapistPreferenceValue': sample_therapists[1].id,
    })
    assert occupied.status_code == 201, occupied.get_json()

    assert client.post('/api/booking-access/challenges', json={'phoneNumber': '+84901234567'}).status_code == 200
    verified = client.post('/api/booking-access/verifications', json={
        'phoneNumber': '0901234567', 'code': delivered[-1],
    })
    assert verified.status_code == 200
    customer = _headers(verified.get_json()['data']['accessToken'])
    stranger = _headers(_token('customer', phone='0901234568'))
    detail_url = f'/api/bookings/{booking_id}'
    original = client.get(detail_url, headers=customer).get_json()['data']
    assert original['preferences']['notes'] == 'Keep this request'

    denied = client.patch(detail_url, headers=customer, json={
        'startTime': '11:00', 'therapistId': sample_therapists[1].id,
    })
    assert denied.status_code == 422
    assert denied.get_json()['error']['code'] == 'SLOT_UNAVAILABLE'
    assert client.get(detail_url, headers=customer).get_json()['data'] == original
    assert client.patch(detail_url, headers=stranger, json={'startTime': '12:00'}).status_code == 404
    assert client.patch(f'{detail_url}/cancel', headers=stranger).status_code == 404

    changed = client.patch(detail_url, headers=customer, json={'startTime': '11:00'})
    assert changed.status_code == 200, changed.get_json()
    updated = client.get(detail_url, headers=customer).get_json()['data']
    assert updated['startTime'] == '11:00'
    assert updated['endTime'] == '12:00'
    assert updated['services'] == original['services']
    assert updated['preferences'] == original['preferences']
    assert updated['therapistAssignments'] == original['therapistAssignments']

    course_change = client.patch(detail_url, headers=customer, json={
        'duration': 90,
        'services': [
            {'personIndex': 1, 'courseId': sample_courses[0].id},
            {'personIndex': 1, 'courseId': sample_courses[1].id},
        ],
        'addOns': [],
        'selectedCourses': [
            {'courseId': sample_courses[0].id, 'duration': 60, 'price': 6000},
            {'courseId': sample_courses[1].id, 'duration': 30, 'price': 3000},
        ],
    })
    assert course_change.status_code == 200, course_change.get_json()
    changed_detail = client.get(detail_url, headers=customer).get_json()['data']
    assert changed_detail['endTime'] == '12:30'
    assert [row['courseId'] for row in changed_detail['services']] == [sample_courses[0].id, sample_courses[1].id]
    assert changed_detail['preferences']['notes'] == 'Keep this request'

    cancelled = client.patch(f'{detail_url}/cancel', headers=customer)
    assert cancelled.status_code == 200
    assert client.get(detail_url, headers=customer).get_json()['data']['status'] == 'Cancelled'
    assert client.patch(detail_url, headers=customer, json={'startTime': '12:00'}).get_json()['error']['code'] == 'INVALID_MODIFY_STATUS'
    repeated = client.patch(f'{detail_url}/cancel', headers=customer)
    assert repeated.status_code == 422
    assert repeated.get_json()['error']['code'] == 'INVALID_CANCEL_STATUS'


def test_public_availability_and_eligibility_do_not_expose_booking_details(client, sample_shop, sample_courses, sample_therapists):
    _create(client, sample_shop, sample_courses[0])
    params = {
        'date': (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
        'duration': 60, 'numberOfPeople': 1, 'show_therapists': 'true',
    }
    public = client.get(f'/api/shops/{sample_shop.id}/available-slots', query_string=params)
    assert public.status_code == 200
    assert 'therapistBookingDetails' not in public.get_json()
    assert client.get(f'/api/admin/shops/{sample_shop.id}/available-slots', query_string=params).status_code == 401
    admin = _headers(_token('admin', user_id=1))
    protected = client.get(f'/api/admin/shops/{sample_shop.id}/available-slots', query_string=params, headers=admin)
    assert protected.status_code == 200
    assert 'therapistBookingDetails' in protected.get_json()

    customer = Customer.query.filter_by(phone_number='0901234567').one()
    customer.member_rank = 'Gold'
    customer.visit_count = 7
    db.session.commit()
    eligibility = client.post('/api/booking-eligibility-checks', json={'phoneNumber': '0901234567'}).get_json()['data']
    assert eligibility == {'isEligible': True, 'isBlocked': False}


def test_group_therapist_membership_for_detail_and_transition(client, sample_shop, sample_courses, sample_therapists):
    booking_id = _create(client, sample_shop, sample_courses[0], guests=2)
    from app.models.booking import Booking
    booking = db.session.get(Booking, booking_id)
    assigned = {row.therapist_id for row in booking.booking_therapists}
    second = next(iter(assigned - {booking.therapist_id}))
    unassigned = next(t.id for t in sample_therapists if t.id not in assigned)
    member = _headers(_token('therapist', user_id=second))
    stranger = _headers(_token('therapist', user_id=unassigned))
    assert [item['bookingId'] for item in client.get('/api/therapists/bookings', headers=member).get_json()['data']] == [booking_id]
    visit_date = booking.booking_date.isoformat()
    schedule = client.get('/api/therapists/me/schedule', query_string={'dateFrom': visit_date, 'dateTo': visit_date}, headers=member)
    assert [item['bookingId'] for item in schedule.get_json()['data']] == [booking_id]
    assert client.get(f'/api/bookings/{booking_id}', headers=member).status_code == 200
    assert client.get(f'/api/bookings/{booking_id}', headers=stranger).status_code == 404
    assert client.patch(f'/api/therapists/bookings/{booking_id}/checkin', headers=stranger).status_code == 403
    assert client.patch(f'/api/therapists/bookings/{booking_id}/checkin', headers=member).status_code == 200
    assert client.patch(f'/api/therapists/bookings/{booking_id}/checkout', headers=member).status_code == 200
