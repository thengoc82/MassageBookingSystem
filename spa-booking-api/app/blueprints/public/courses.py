from app.blueprints.public import public_bp
from app.models.course import Course
from app.models.shop import Shop
from app.utils import success_response
from app.utils.errors import ResourceNotFound
from flask import request


@public_bp.route('/shops/<int:shop_id>/courses', methods=['GET'])
def get_courses(shop_id):
    shop = Shop.query.get(shop_id)
    if not shop:
        raise ResourceNotFound('Shop')

    course_type = request.args.get('type')

    query = Course.query.filter_by(shop_id=shop_id, status='active')

    if course_type and course_type in ['main', 'addon']:
        query = query.filter_by(course_type=course_type)

    courses = query.all()

    data = [{
        'courseId': course.id,
        'courseName': course.name,
        'durations': course.get_durations(),
        'courseType': course.course_type
    } for course in courses]

    return success_response(data)
