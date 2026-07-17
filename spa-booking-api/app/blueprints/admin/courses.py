from flask import request
from app.blueprints.admin import admin_bp
from app.utils.decorators import role_required
from app.models.course import Course
from app.models.shop import Shop
from app.extensions import db
from app.utils import success_response
from app.utils.errors import ResourceNotFound, ValidationError

@admin_bp.route('/shops/<int:shop_id>/courses', methods=['GET'])
@role_required('admin')
def get_courses(shop_id):
    course_type = request.args.get('type')
    status = request.args.get('status')
    
    query = Course.query.filter_by(shop_id=shop_id)
    
    if course_type:
        query = query.filter_by(course_type=course_type)
    
    if status:
        query = query.filter_by(status=status)
    
    courses = query.all()
    
    data = [{
        'courseId': course.id,
        'courseName': course.name,
        'duration': course.duration,
        'price': course.price,
        'courseType': course.course_type,
        'status': course.status
    } for course in courses]
    
    return success_response(data)

@admin_bp.route('/shops/<int:shop_id>/courses', methods=['POST'])
@role_required('admin')
def create_course(shop_id):
    shop = Shop.query.get(shop_id)
    if not shop:
        raise ResourceNotFound('Shop')
    
    data = request.get_json()
    
    if not data.get('courseName'):
        raise ValidationError('courseName is required')
    
    if not data.get('duration') or data['duration'] <= 0:
        raise ValidationError('duration must be greater than 0')
    
    if 'price' not in data or data['price'] < 0:
        raise ValidationError('price must be 0 or greater')
    
    if data.get('courseType') not in ['main', 'addon']:
        raise ValidationError('courseType must be main or addon')
    
    course = Course(
        shop_id=shop_id,
        name=data['courseName'],
        duration=data['duration'],
        price=data['price'],
        course_type=data['courseType']
    )
    
    db.session.add(course)
    db.session.commit()
    
    return success_response({'courseId': course.id}, message='Course created', status_code=201)
