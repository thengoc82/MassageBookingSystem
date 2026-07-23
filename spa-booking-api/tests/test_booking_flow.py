from datetime import datetime, timedelta

def test_create_booking_directly_returns_201(client, sample_shop, sample_courses, sample_therapists):
    """POST /api/bookings with direct data should return 201 with booking code."""
    course = sample_courses[0]
    today = datetime.utcnow().date()
    # Use a future date
    future = today + timedelta(days=7)
    date_str = future.strftime('%Y-%m-%d')

    # Ensure it's a weekday (shift coverage exists for all days in fixtures)
    payload = {
        'phoneNumber': '0987654321',
        'shopId': sample_shop.id,
        'bookingDate': date_str,
        'startTime': '10:00',
        'duration': course.duration,
        'numberOfPeople': 1,
        'courseId': course.id,
        'services': [{'personIndex': 1, 'courseId': course.id}],
        'addOns': []
    }
    resp = client.post('/api/bookings', json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['data']['bookingCode'].startswith('BK')
    assert data['data']['status'] == 'Booked'


def test_create_booking_rejects_missing_phone(client, sample_shop, sample_courses):
    """POST /api/bookings without phoneNumber should return 400."""
    course = sample_courses[0]
    payload = {
        'shopId': sample_shop.id,
        'bookingDate': '2026-07-20',
        'startTime': '10:00',
        'duration': course.duration,
        'numberOfPeople': 1,
        'courseId': course.id,
        'services': [{'personIndex': 1, 'courseId': course.id}]
    }
    resp = client.post('/api/bookings', json=payload)
    assert resp.status_code == 400
    assert resp.get_json()['error']['code'] == 'VALIDATION_ERROR'


def test_create_booking_fails_for_blocked_customer(client, sample_shop, sample_courses):
    """POST /api/bookings for a blocked customer should fail."""
    from app.models.customer import Customer
    from app.models.customer_restriction import CustomerRestriction
    from app.extensions import db

    customer = Customer(phone_number='0999999999', member_rank='Silver')
    db.session.add(customer)
    db.session.flush()

    restriction = CustomerRestriction(customer_id=customer.id, phone_number='0999999999', blocked_by='admin', reason='Violation', is_active=True)
    db.session.add(restriction)
    db.session.commit()

    course = sample_courses[0]
    payload = {
        'phoneNumber': '0999999999',
        'shopId': sample_shop.id,
        'bookingDate': '2026-07-20',
        'startTime': '10:00',
        'duration': course.duration,
        'numberOfPeople': 1,
        'courseId': course.id,
        'services': [{'personIndex': 1, 'courseId': course.id}]
    }
    resp = client.post('/api/bookings', json=payload)
    assert resp.status_code == 422
    assert resp.get_json()['error']['code'] == 'CUSTOMER_BLOCKED'


def test_available_therapists_returns_200(client, sample_shop, sample_therapists):
    """GET /api/shops/{id}/available-therapists should return 200 with therapist list."""
    resp = client.get(f'/api/shops/{sample_shop.id}/available-therapists', query_string={
        'date': '2026-07-20',
        'startTime': '10:00',
        'duration': 60
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    therapists = data['data']
    assert len(therapists) == 3
    names = [t['name'] for t in therapists]
    assert 'Therapist A' in names


def test_get_available_slots_returns_capacity(client, sample_shop, sample_therapists):
    """GET /api/shops/{id}/available-slots should return slots with correct capacity."""
    resp = client.get(f'/api/shops/{sample_shop.id}/available-slots', query_string={
        'date': '2026-07-30',
        'duration': 60,
        'numberOfPeople': 2
    })
    assert resp.status_code == 200
    data = resp.get_json()
    slots = data.get('data') if isinstance(data, dict) and 'data' in data else data
    assert len(slots) > 0
    for slot in slots:
        assert slot['availableCapacity'] >= 0


def test_get_available_slots_with_therapists(client, sample_shop, sample_therapists):
    """GET /api/shops/{id}/available-slots?show_therapists=true returns all slots with therapist-level availability."""
    resp = client.get(f'/api/shops/{sample_shop.id}/available-slots', query_string={
        'date': '2026-07-30',
        'duration': 60,
        'numberOfPeople': 1,
        'show_therapists': 'true'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    therapists = data['therapists']
    assert len(therapists) == 3
    assert all('name' in t and 'therapistId' in t for t in therapists)
    slots = data['data']
    assert len(slots) > 0
    # All shop slots are returned (not just available ones) so the grid stays stable
    for slot in slots:
        assert 'availableTherapistIds' in slot
        assert isinstance(slot['availableTherapistIds'], list)
        for tid in slot['availableTherapistIds']:
            assert tid in [t['therapistId'] for t in therapists]
