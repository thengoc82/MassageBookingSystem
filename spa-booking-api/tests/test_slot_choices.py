from datetime import datetime, timedelta

import pytest

from app.extensions import db


def _date():
    return (datetime.utcnow().date() + timedelta(days=7)).isoformat()


def _slots(client, shop_id, **overrides):
    params = {'date': _date(), 'duration': 60, 'numberOfPeople': 1, **overrides}
    return client.get(f'/api/shops/{shop_id}/available-slots', query_string=params)


def test_gender_slots_match_create_time_eligibility(client, sample_shop, sample_courses, sample_therapists):
    male = sample_therapists[1]
    response = _slots(client, sample_shop.id, gender='Male', show_therapists='true')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert [item['therapistId'] for item in response.json['therapists']] == [male.id]
    at_ten = next(slot for slot in response.json['data'] if slot['startTime'] == '10:00')
    assert at_ten['availableCapacity'] == 1
    assert at_ten['availableTherapistIds'] == [male.id]

    booked = client.post('/api/bookings', json={
        'phoneNumber': '0901234567', 'shopId': sample_shop.id,
        'bookingDate': _date(), 'startTime': '10:00', 'duration': 60,
        'courseId': sample_courses[0].id,
        'therapistPreferenceType': 'specific', 'therapistPreferenceValue': male.id,
    })
    assert booked.status_code == 201
    assert not any(slot['startTime'] == '10:00' for slot in _slots(client, sample_shop.id, gender='Male').json['data'])
    at_ten = next(slot for slot in _slots(client, sample_shop.id, gender='Male', show_therapists='true').json['data']
                  if slot['startTime'] == '10:00')
    assert at_ten['availableCapacity'] == 0
    assert at_ten['availableTherapistIds'] == []
    assert any(slot['startTime'] == '10:00' for slot in _slots(client, sample_shop.id, gender='Female').json['data'])


def test_closed_shop_and_early_start_do_not_offer_unbookable_times(client, sample_shop, sample_therapists):
    early = _slots(client, sample_shop.id, startTime='07:00', show_therapists='true')
    assert early.status_code == 200
    assert early.json['data'][0]['startTime'] == '08:00'
    assert _slots(client, sample_shop.id, startTime='08:07', show_therapists='true').json['data'][0]['startTime'] == '08:15'
    sample_shop.status = 'Closed'
    db.session.commit()
    assert _slots(client, sample_shop.id).json['data'] == []
    assert _slots(client, sample_shop.id, show_therapists='true').json['data'] == []


@pytest.mark.parametrize('override', [
    {'date': '2026-99-01'}, {'date': '2026-1-01'},
    {'startTime': '7:00'}, {'startTime': '25:00'},
    {'duration': -15}, {'numberOfPeople': -1},
    {'gender': 'Other'}, {'gender': 'Female', 'numberOfPeople': 2},
])
def test_bad_slot_queries_return_validation_error(client, sample_shop, override):
    response = _slots(client, sample_shop.id, **override)
    assert response.status_code == 400
    assert response.json['error']['code'] == 'VALIDATION_ERROR'
