from app.blueprints.public import public_bp
from app.models.course import Course
from app.models.shop import Shop
from app.utils import success_response
from app.utils.errors import ResourceNotFound, ValidationError
from flask import request


@public_bp.route('/shops/<int:shop_id>/courses', methods=['GET'])
def get_courses(shop_id):
    shop = Shop.query.get(shop_id)
    if not shop or shop.status != 'Open':
        raise ResourceNotFound('Shop')

    course_type = request.args.get('type')

    query = Course.query.filter_by(shop_id=shop_id, status='active')

    if course_type and course_type not in ('main', 'addon'):
        raise ValidationError('type must be main or addon')
    if course_type:
        query = query.filter_by(course_type=course_type)

    courses = [(course, course.get_bookable_durations()) for course in query.all()]

    data = [{
        'courseId': course.id,
        'courseName': course.name,
        'durations': options,
        'courseType': course.course_type
    } for course, options in courses if options]

    return success_response(data)
