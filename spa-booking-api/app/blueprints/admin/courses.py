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
        'durations': course.get_durations(),
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

    durations = data.get('durations', [])
    if not durations or not isinstance(durations, list):
        raise ValidationError('durations array is required')

    for entry in durations:
        if entry.get('duration', 0) <= 0:
            raise ValidationError('each duration must be greater than 0')
        if entry.get('price', -1) < 0:
            raise ValidationError('each price must be 0 or greater')

    if data.get('courseType') not in ['main', 'addon']:
        raise ValidationError('courseType must be main or addon')

    course = Course(
        shop_id=shop_id,
        name=data['courseName'],
        course_type=data['courseType']
    )
    course.set_durations(durations)

    db.session.add(course)
    db.session.commit()

    return success_response({
        'courseId': course.id,
        'courseName': course.name,
        'durations': course.get_durations(),
        'courseType': course.course_type
    }, message='Course created', status_code=201)
