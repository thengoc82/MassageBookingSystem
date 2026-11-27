from datetime import datetime, timedelta

from app.extensions import db
from app.models import Booking, Course


def test_public_catalog_only_returns_bookable_options(client, sample_shop):
    main = Course(shop_id=sample_shop.id, name='Main', course_type='main')
    main.set_durations([{'duration': 30, 'price': 0}, {'duration': 0, 'price': 5}, {'duration': 60, 'price': -1}])
    addon = Course(shop_id=sample_shop.id, name='Extra', course_type='addon', duration=15, price=100)
    empty = Course(shop_id=sample_shop.id, name='Invalid', course_type='addon', duration=0, price=50)
    inactive = Course(shop_id=sample_shop.id, name='Inactive', course_type='main', duration=30, price=100, status='inactive')
    db.session.add_all([main, addon, empty, inactive])
    db.session.commit()

    response = client.get(f'/api/shops/{sample_shop.id}/courses')
    assert response.status_code == 200
    assert response.json['data'] == [
        {'courseId': main.id, 'courseName': 'Main', 'courseType': 'main', 'durations': [{'duration': 30, 'price': 0}]},
        {'courseId': addon.id, 'courseName': 'Extra', 'courseType': 'addon', 'durations': [{'duration': 15, 'price': 100}]},
    ]
    assert [item['courseId'] for item in client.get(f'/api/shops/{sample_shop.id}/courses?type=addon').json['data']] == [addon.id]
    assert client.get(f'/api/shops/{sample_shop.id}/courses?type=unknown').status_code == 400


def test_closed_shop_has_no_public_catalog(client, sample_shop):
    sample_shop.status = 'Closed'
    db.session.commit()
    assert client.get(f'/api/shops/{sample_shop.id}/courses').status_code == 404


def test_discovered_main_and_addon_options_create_group_booking(client, sample_shop, sample_therapists):
    main = Course(shop_id=sample_shop.id, name='Main', course_type='main')
    main.set_durations([{'duration': 30, 'price': 3000}])
    addon = Course(shop_id=sample_shop.id, name='Extra', course_type='addon')
    addon.set_durations([{'duration': 15, 'price': 500}])
    db.session.add_all([main, addon])
    db.session.commit()

    catalog = client.get(f'/api/shops/{sample_shop.id}/courses').json['data']
    choices = [{'courseId': item['courseId'], **item['durations'][0]} for item in catalog]
    booking_date = (datetime.utcnow().date() + timedelta(days=2)).isoformat()
    response = client.post('/api/bookings', json={
        'shopId': sample_shop.id, 'phoneNumber': '0901234567',
        'bookingDate': booking_date, 'startTime': '10:00', 'duration': 45,
        'numberOfPeople': 2,
        'services': [{'personIndex': index, 'courseId': main.id} for index in (1, 2)],
        'addOns': [{'personIndex': index, 'courseId': addon.id} for index in (1, 2)],
        'selectedCourses': choices,
    })
    assert response.status_code == 201
    booking = db.session.get(Booking, response.json['data']['bookingId'])
    assert [(item.person_index, item.course_id) for item in booking.services] == [(1, main.id), (2, main.id)]
    assert [(item.person_index, item.course_id) for item in booking.addons] == [(1, addon.id), (2, addon.id)]
