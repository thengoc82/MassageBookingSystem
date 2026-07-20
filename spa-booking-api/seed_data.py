import os
import sys
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Shop, Course, Therapist, User

app = create_app()

with app.app_context():
    print("Seeding database with sample data...")
    
    # Check if data already exists
    existing_shop = Shop.query.first()
    if existing_shop:
        print("Data already exists! Skipping...")
        sys.exit(0)
    
    # Create shop
    shop = Shop(
        name='ABC Spa',
        address='123 Main Street, District 1, Ho Chi Minh City',
        phone_number='0123456789',
        status='Open',
        open_time=time(8, 0),
        close_time=time(21, 0)
    )
    db.session.add(shop)
    db.session.flush()
    
    # Create courses
    courses_data = [
        {'name': 'Thai Massage', 'duration': 60, 'price': 500000, 'type': 'main'},
        {'name': 'Swedish Massage', 'duration': 90, 'price': 700000, 'type': 'main'},
        {'name': 'Deep Tissue Massage', 'duration': 60, 'price': 600000, 'type': 'main'},
        {'name': 'Hot Stone Massage', 'duration': 90, 'price': 800000, 'type': 'main'},
        {'name': 'Aromatherapy', 'duration': 30, 'price': 200000, 'type': 'addon'},
        {'name': 'Foot Massage', 'duration': 30, 'price': 150000, 'type': 'addon'},
        {'name': 'Head Massage', 'duration': 20, 'price': 100000, 'type': 'addon'},
    ]
    
    for course_data in courses_data:
        course = Course(
            shop_id=shop.id,
            name=course_data['name'],
            duration=course_data['duration'],
            price=course_data['price'],
            course_type=course_data['type'],
            status='active'
        )
        db.session.add(course)
    
    # Create therapists
    therapists_data = [
        {'name': 'Anna Nguyen', 'gender': 'Female', 'phone': '0987654321'},
        {'name': 'John Smith', 'gender': 'Male', 'phone': '0987654322'},
        {'name': 'Lisa Tran', 'gender': 'Female', 'phone': '0987654323'},
        {'name': 'David Lee', 'gender': 'Male', 'phone': '0987654324'},
    ]
    
    for therapist_data in therapists_data:
        therapist = Therapist(
            shop_id=shop.id,
            name=therapist_data['name'],
            gender=therapist_data['gender'],
            phone_number=therapist_data['phone'],
            status='active'
        )
        db.session.add(therapist)
    
    admin = User(username='admin', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)

    therapist_creds = [
        ('anna', 'anna123'),
        ('john', 'john123'),
        ('lisa', 'lisa123'),
        ('david', 'david123'),
    ]
    therapists_list = Therapist.query.all()
    for t, (un, pw) in zip(therapists_list, therapist_creds):
        t.username = un
        t.set_password(pw)

    db.session.commit()
    
    print("✓ Seeding complete!")
    print("\n=== Sample Data Created ===")
    print(f"Shop: {shop.name}")
    print(f"Courses: {len(courses_data)} (4 main, 3 addons)")
    print(f"Therapists: {len(therapists_data)}")
    print("\n=== Accounts ===")
    print("Admin:   admin / admin123")
    for t, (un, _) in zip(therapists_list, therapist_creds):
        print(f"{t.name}: {un} / {un}123")
    print("\n=== Ready to use! ===")
    print("Frontend: http://localhost:3000")
    print("Backend:  http://localhost:5000")
