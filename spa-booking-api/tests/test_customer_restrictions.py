from datetime import datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Customer, CustomerRestriction


def _headers(role='admin'):
    token = create_access_token(identity={
        'role': role, 'type': role, 'user_id': 1, 'username': 'admin-test',
    })
    return {'Authorization': f'Bearer {token}'}


def _booking(shop, course, phone='0987654321'):
    return {
        'phoneNumber': phone,
        'shopId': shop.id,
        'bookingDate': (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
        'startTime': '10:00',
        'duration': 60,
        'numberOfPeople': 1,
        'courseId': course.id,
    }


def test_restriction_routes_require_admin(client):
    routes = [
        ('get', '/api/admin/customer-restrictions'),
        ('post', '/api/admin/customer-restrictions'),
        ('get', '/api/admin/customer-restrictions/1'),
        ('patch', '/api/admin/customer-restrictions/1'),
        ('delete', '/api/admin/customer-restrictions/1'),
    ]
    for method, route in routes:
        assert getattr(client, method)(route).status_code == 401
        assert getattr(client, method)(route, headers=_headers('therapist')).status_code == 403
        assert getattr(client, method)(route, headers=_headers('customer')).status_code == 403


def test_block_edit_remove_and_rebook(client, sample_shop, sample_customer,
                                      sample_courses, sample_therapists):
    headers = _headers()
    payload = _booking(sample_shop, sample_courses[0])
    first = client.post('/api/bookings', json=payload)
    assert first.status_code == 201, first.get_json()

    created = client.post('/api/admin/customer-restrictions',
                          json={'phoneNumber': sample_customer.phone_number, 'reason': 'No show'},
                          headers=headers)
    assert created.status_code == 201, created.get_json()
    entry = created.get_json()['data']
    restriction_id = entry['restrictionId']
    assert entry['blockedBy'] == 'admin-test'
    assert entry['reason'] == 'No show'
    assert entry['isActive'] is True
    assert sample_customer.is_blocked is True
    assert client.get(f'/api/admin/customer-restrictions/{restriction_id}',
                      headers=headers).get_json()['data'] == entry
    assert client.get('/api/admin/customers', query_string={'blocked': 'true'},
                      headers=headers).get_json()['data'][0]['isBlocked'] is True

    public = client.post('/api/booking-eligibility-checks',
                         json={'phoneNumber': sample_customer.phone_number})
    assert public.get_json()['data'] == {'isEligible': False, 'isBlocked': True}
    assert 'No show' not in str(public.get_json())
    blocked = client.post('/api/bookings', json={**payload, 'startTime': '11:00'})
    assert blocked.status_code == 422
    assert blocked.get_json()['error']['code'] == 'CUSTOMER_BLOCKED'
    assert 'No show' not in str(blocked.get_json())

    edited = client.patch(f'/api/admin/customer-restrictions/{restriction_id}',
                          json={'reason': 'Repeated no shows'}, headers=headers)
    assert edited.status_code == 200
    assert edited.get_json()['data']['reason'] == 'Repeated no shows'
    assert client.delete(f'/api/admin/customer-restrictions/{restriction_id}',
                         headers=headers).status_code == 200
    assert sample_customer.is_blocked is False
    assert client.get('/api/admin/customer-restrictions', headers=headers).get_json()['data'] == []
    history = client.get('/api/admin/customer-restrictions',
                         query_string={'status': 'inactive'}, headers=headers).get_json()
    assert history['data'][0]['restrictionId'] == restriction_id
    assert history['data'][0]['isActive'] is False
    assert client.post('/api/booking-eligibility-checks',
                       json={'phoneNumber': sample_customer.phone_number}).get_json()['data']['isEligible'] is True
    rebooked = client.post('/api/bookings', json={**payload, 'startTime': '11:00'})
    assert rebooked.status_code == 201, rebooked.get_json()
    assert first.get_json()['data']['bookingId'] != rebooked.get_json()['data']['bookingId']


def test_reblock_creates_history_and_filters_are_paginated(client, sample_customer):
    headers = _headers()
    url = '/api/admin/customer-restrictions'
    first = client.post(url, json={'phoneNumber': sample_customer.phone_number, 'reason': 'First'},
                        headers=headers).get_json()['data']['restrictionId']
    duplicate = client.post(url, json={'phoneNumber': sample_customer.phone_number, 'reason': 'Again'},
                            headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.get_json()['error']['code'] == 'CUSTOMER_ALREADY_BLOCKED'
    assert client.patch(f'{url}/{first}', json={'isActive': False}, headers=headers).status_code == 200
    second = client.post(url, json={'phoneNumber': sample_customer.phone_number, 'reason': 'Again'},
                         headers=headers).get_json()['data']['restrictionId']
    assert second != first
    result = client.get(url, query_string={
        'status': 'all', 'phone': '0987', 'page': 2, 'size': 1,
    }, headers=headers).get_json()
    assert result['pagination'] == {'page': 2, 'size': 1, 'total': 2, 'totalPages': 2}
    assert result['data'][0]['restrictionId'] == first
    assert client.delete(f'{url}/{second}', headers=headers).status_code == 200
    assert sample_customer.is_blocked is False


def test_invalid_restriction_requests_and_missing_customer(client, sample_customer):
    headers = _headers()
    url = '/api/admin/customer-restrictions'
    for body in (None, [], {}, {'phoneNumber': sample_customer.phone_number, 'reason': '  '},
                 {'phoneNumber': sample_customer.phone_number, 'reason': 'x', 'isActive': True}):
        response = client.post(url, json=body, headers=headers)
        assert response.status_code == 400, response.get_json()
    assert client.post(url, json={'phoneNumber': '0900000000', 'reason': 'x'},
                       headers=headers).status_code == 404
    assert client.get(url, query_string={'status': 'bad'}, headers=headers).status_code == 400
    assert client.get(url, query_string={'page': 'zero'}, headers=headers).status_code == 400
    assert client.get(url, query_string={'size': 101}, headers=headers).status_code == 400
    assert client.get(f'{url}/9999', headers=headers).status_code == 404
    assert client.patch(f'{url}/9999', json={'reason': 'x'}, headers=headers).status_code == 404
    assert client.delete(f'{url}/9999', headers=headers).status_code == 404
    created = client.post(url, json={'phoneNumber': sample_customer.phone_number, 'reason': 'x'},
                          headers=headers).get_json()['data']['restrictionId']
    for body in (None, {}, [], {'reason': ''}, {'isActive': True}, {'customerId': 2}):
        assert client.patch(f'{url}/{created}', json=body, headers=headers).status_code == 400
    assert sample_customer.is_blocked is True


def test_phone_aliases_cannot_bypass_restriction(client, sample_shop, sample_customer,
                                                 sample_courses, sample_therapists):
    headers = _headers()
    alias = '+84' + sample_customer.phone_number[1:]
    created = client.post('/api/admin/customer-restrictions',
                          json={'phoneNumber': alias, 'reason': 'Do not book'}, headers=headers)
    assert created.status_code == 201
    assert client.post('/api/bookings', json=_booking(sample_shop, sample_courses[0], alias)).status_code == 422
    assert client.post('/api/booking-eligibility-checks',
                       json={'phoneNumber': alias}).get_json()['data']['isBlocked'] is True


def test_removing_one_of_multiple_active_restrictions_keeps_customer_blocked(client, sample_customer):
    headers = _headers()
    records = [CustomerRestriction(customer_id=sample_customer.id,
                                   phone_number=sample_customer.phone_number,
                                   reason=f'Older reason {i}', blocked_by='admin', is_active=True)
               for i in range(2)]
    db.session.add_all(records)
    db.session.commit()
    assert client.delete(f'/api/admin/customer-restrictions/{records[0].id}', headers=headers).status_code == 200
    assert sample_customer.is_blocked is True
    assert client.post('/api/booking-eligibility-checks',
                       json={'phoneNumber': sample_customer.phone_number}).get_json()['data']['isBlocked'] is True


def test_legacy_flag_migration_preserves_block(client, sample_customer, monkeypatch):
    sample_customer.is_blocked = True
    db.session.commit()
    assert client.post('/api/booking-eligibility-checks',
                       json={'phoneNumber': sample_customer.phone_number}).get_json()['data']['isBlocked'] is True
    path = Path(__file__).resolve().parents[1] / 'migrations' / 'versions' / '20261126_reconcile_customer_restrictions.py'
    spec = spec_from_file_location('restriction_migration', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.op, 'get_bind', lambda: db.session.connection())
    module.upgrade()
    db.session.commit()
    records = CustomerRestriction.query.filter_by(customer_id=sample_customer.id, is_active=True).all()
    assert len(records) == 1
    assert records[0].blocked_by == 'legacy migration'
    assert client.post('/api/booking-eligibility-checks',
                       json={'phoneNumber': sample_customer.phone_number}).get_json()['data']['isBlocked'] is True
    module.upgrade()  # Re-running does not duplicate a legacy entry.
    db.session.commit()
    assert CustomerRestriction.query.filter_by(customer_id=sample_customer.id).count() == 1
