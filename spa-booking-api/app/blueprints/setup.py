from flask import Blueprint, jsonify
from app.extensions import db
from app.models import Shop, Course, Therapist, User
from datetime import time

setup_bp = Blueprint('setup', __name__)

@setup_bp.route('/setup-demo-data', methods=['POST'])
def setup_demo_data():
    existing_shop = Shop.query.first()
    if existing_shop:
        return jsonify({
            'success': False,
            'message': 'Demo data already exists'
        }), 400
    
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
    
    course_defs = [
        {'name': 'Thai Massage', 'type': 'main', 'durations': [{'duration': 15, 'price': 150000}, {'duration': 30, 'price': 300000}, {'duration': 45, 'price': 400000}, {'duration': 60, 'price': 500000}]},
        {'name': 'Swedish Massage', 'type': 'main', 'durations': [{'duration': 15, 'price': 200000}, {'duration': 30, 'price': 400000}, {'duration': 45, 'price': 550000}, {'duration': 60, 'price': 700000}]},
        {'name': 'Deep Tissue', 'type': 'main', 'durations': [{'duration': 15, 'price': 180000}, {'duration': 30, 'price': 350000}, {'duration': 45, 'price': 500000}, {'duration': 60, 'price': 600000}]},
        {'name': 'Hot Stone Massage', 'type': 'main', 'durations': [{'duration': 15, 'price': 250000}, {'duration': 30, 'price': 450000}, {'duration': 45, 'price': 650000}, {'duration': 60, 'price': 800000}]},
        {'name': 'Aromatherapy', 'type': 'addon', 'durations': [{'duration': 15, 'price': 100000}, {'duration': 30, 'price': 200000}]},
        {'name': 'Foot Massage', 'type': 'addon', 'durations': [{'duration': 15, 'price': 80000}, {'duration': 30, 'price': 150000}]},
        {'name': 'Head Massage', 'type': 'addon', 'durations': [{'duration': 10, 'price': 50000}, {'duration': 20, 'price': 100000}]},
    ]
    
    for cd in course_defs:
        course = Course(shop_id=shop.id, name=cd['name'], course_type=cd['type'], status='active')
        course.set_durations(cd['durations'])
        db.session.add(course)
    
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

    therapists_list = Therapist.query.all()
    therapist_creds = [
        ('anna', 'anna123'),
        ('john', 'john123'),
        ('lisa', 'lisa123'),
        ('david', 'david123'),
    ]
    for t, (un, pw) in zip(therapists_list, therapist_creds):
        t.username = un
        t.set_password(pw)

    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Demo data created successfully',
        'data': {
            'shop': shop.name,
            'courses': len(courses_data),
            'therapists': len(therapists_data),
            'accounts': {
                'admin': {'username': 'admin', 'password': 'admin123'},
                'therapists': {t.name: {'username': un, 'password': pw}
                              for t, (un, pw) in zip(therapists_list, therapist_creds)}
            }
        }
    }), 201
