import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from app.extensions import db
from app.models import Shop, Course, Therapist, TherapistShift, User
from datetime import time, date

app = create_app()
with app.app_context():
    existing = Shop.query.first()
    if existing:
        print('Data already exists')
        sys.exit(0)

    shop = Shop(name='Shinjuku Store', address='1-2-3 Shinjuku, Tokyo',
                phone_number='03-1234-5678', status='Open',
                open_time=time(9, 0), close_time=time(21, 0))
    db.session.add(shop)
    db.session.flush()

    shop2 = Shop(name='Shibuya Store', address='4-5-6 Shibuya, Tokyo',
                 phone_number='03-8765-4321', status='Open',
                 open_time=time(10, 0), close_time=time(22, 0))
    db.session.add(shop2)
    db.session.flush()

    courses = [
        Course(shop_id=shop.id, name='Full Body Massage', duration=60, price=6000, course_type='main'),
        Course(shop_id=shop.id, name='Full Body Massage', duration=90, price=9000, course_type='main'),
        Course(shop_id=shop.id, name='Full Body Massage', duration=120, price=12000, course_type='main'),
        Course(shop_id=shop.id, name='Dry Head Spa', duration=30, price=3000, course_type='main'),
        Course(shop_id=shop.id, name='Dry Head Spa', duration=60, price=5500, course_type='main'),
        Course(shop_id=shop.id, name='Aromatherapy', duration=60, price=7000, course_type='main'),
        Course(shop_id=shop.id, name='Premium Mattress', duration=0, price=1500, course_type='addon'),
        Course(shop_id=shop.id, name='Foot Reflexology', duration=0, price=2000, course_type='addon'),
    ]
    for c in courses:
        db.session.add(c)

    therapists = [
        Therapist(shop_id=shop.id, name='Tanaka Yuki', gender='Female', status='active'),
        Therapist(shop_id=shop.id, name='Suzuki Kenji', gender='Male', status='active'),
        Therapist(shop_id=shop.id, name='Sato Mei', gender='Female', status='active'),
        Therapist(shop_id=shop.id, name='Yamada Taro', gender='Male', status='active'),
        Therapist(shop_id=shop.id, name='Watanabe Aoi', gender='Female', status='active'),
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

    admin = User(username='admin', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)

    therapist_creds = [
        ('tanaka', 'tanaka123'),
        ('suzuki', 'suzuki123'),
        ('sato', 'sato123'),
        ('yamada', 'yamada123'),
        ('watanabe', 'watanabe123'),
    ]
    for t, (un, pw) in zip(therapists, therapist_creds):
        t.username = un
        t.set_password(pw)

    db.session.commit()
    print(f'Seeded: {len(courses)} courses, {len(therapists)} therapists, 2 shops')
    print('Admin: admin / admin123')
    for t, (un, _) in zip(therapists, therapist_creds):
        print(f'Therapist {t.name}: {un} / {un}123')
