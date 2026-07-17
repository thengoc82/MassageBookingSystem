import pytest
from app import create_app
from app.extensions import db
from app.models import Shop, Customer, Course, Therapist, TherapistShift
from datetime import time, date, datetime, timedelta

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_shop(app):
    shop = Shop(
        name='Test Spa',
        address='123 Test St',
        phone_number='0123456789',
        status='Open',
        open_time=time(8, 0),
        close_time=time(21, 0)
    )
    db.session.add(shop)
    db.session.commit()
    return shop

@pytest.fixture
def sample_customer(app):
    customer = Customer(
        phone_number='0987654321',
        member_rank='Silver'
    )
    db.session.add(customer)
    db.session.commit()
    return customer

@pytest.fixture
def sample_courses(sample_shop):
    courses = [
        Course(shop_id=sample_shop.id, name='Full Body', duration=60, price=6000, course_type='main'),
        Course(shop_id=sample_shop.id, name='Head Spa', duration=30, price=3000, course_type='main'),
        Course(shop_id=sample_shop.id, name='Premium Mat', duration=0, price=1500, course_type='addon'),
    ]
    for c in courses:
        db.session.add(c)
    db.session.commit()
    return courses

@pytest.fixture
def sample_therapists(sample_shop):
    therapists = [
        Therapist(shop_id=sample_shop.id, name='Therapist A', gender='Female', status='active'),
        Therapist(shop_id=sample_shop.id, name='Therapist B', gender='Male', status='active'),
        Therapist(shop_id=sample_shop.id, name='Therapist C', gender='Female', status='active'),
    ]
    for t in therapists:
        db.session.add(t)
    db.session.flush()

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for t in therapists:
        for day in days:
            db.session.add(TherapistShift(
                therapist_id=t.id, day_of_week=day,
                start_time=time(9, 0), end_time=time(21, 0),
                effective_from=date(2026, 1, 1)
            ))
    db.session.commit()
    return therapists
