from app.blueprints.admin import admin_bp
from app.extensions import db
from app.models.course import Course
from app.models.shop import Shop
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import ResourceNotFound, ValidationError
from flask import request


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


@admin_bp.route('/shops/<int:shop_id>/courses/<int:course_id>', methods=['PATCH'])
@role_required('admin')
def update_course(shop_id, course_id):
    course = Course.query.filter_by(id=course_id, shop_id=shop_id).first()
    if not course:
        raise ResourceNotFound('Course')

    data = request.get_json()

    if 'courseName' in data:
        course.name = data['courseName']

    if 'durations' in data:
        durations = data['durations']
        if not isinstance(durations, list) or len(durations) == 0:
            raise ValidationError('durations must be a non-empty array')
        for entry in durations:
            if entry.get('duration', 0) <= 0:
                raise ValidationError('each duration must be greater than 0')
            if entry.get('price', -1) < 0:
                raise ValidationError('each price must be 0 or greater')
        course.set_durations(durations)

    if 'courseType' in data:
        if data['courseType'] not in ['main', 'addon']:
            raise ValidationError('courseType must be main or addon')
        course.course_type = data['courseType']

    if 'status' in data:
        course.status = data['status']

    db.session.commit()

    return success_response({
        'courseId': course.id,
        'courseName': course.name,
        'durations': course.get_durations(),
        'courseType': course.course_type,
        'status': course.status
    }, message='Course updated')


@admin_bp.route('/shops/<int:shop_id>/courses/<int:course_id>', methods=['DELETE'])
@role_required('admin')
def delete_course(shop_id, course_id):
    course = Course.query.filter_by(id=course_id, shop_id=shop_id).first()
    if not course:
        raise ResourceNotFound('Course')

    course.status = 'inactive'
    db.session.commit()

    return success_response({'courseId': course.id}, message='Course deactivated')
