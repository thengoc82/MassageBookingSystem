from app.blueprints.admin import admin_bp
from app.extensions import db
from app.models.shop import Shop
from app.models.therapist import Therapist
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import ResourceNotFound, ValidationError
from flask import request


@admin_bp.route('/shops/<int:shop_id>/therapists', methods=['GET'])
@role_required('admin')
def get_therapists(shop_id):
    gender = request.args.get('gender')
    status = request.args.get('status')

    query = Therapist.query.filter_by(shop_id=shop_id)

    if gender:
        query = query.filter_by(gender=gender)

    if status:
        query = query.filter_by(status=status)

    therapists = query.all()

    data = [{
        'therapistId': t.id,
        'name': t.name,
        'gender': t.gender,
        'phoneNumber': t.phone_number,
        'status': t.status
    } for t in therapists]

    return success_response(data)

@admin_bp.route('/shops/<int:shop_id>/therapists', methods=['POST'])
@role_required('admin')
def create_therapist(shop_id):
    shop = Shop.query.get(shop_id)
    if not shop:
        raise ResourceNotFound('Shop')

    data = request.get_json()

    if not data.get('name'):
        raise ValidationError('name is required')

    if data.get('gender') not in ['Male', 'Female']:
        raise ValidationError('gender must be Male or Female')

    if not data.get('username'):
        raise ValidationError('username is required')

    if not data.get('password'):
        raise ValidationError('password is required')

    therapist = Therapist(
        shop_id=shop_id,
        name=data['name'],
        gender=data['gender'],
        phone_number=data.get('phoneNumber'),
        username=data['username']
    )
    therapist.set_password(data['password'])

    db.session.add(therapist)
    db.session.commit()

    return success_response(
        {'therapistId': therapist.id},
        message='Therapist created',
        status_code=201
    )


@admin_bp.route('/therapists/<int:therapist_id>/schedule', methods=['GET'])
@role_required('admin')
def get_therapist_schedule(therapist_id):
    from app.services.therapist_service import TherapistService
    from app.utils.errors import ResourceNotFound

    therapist = Therapist.query.get(therapist_id)
    if not therapist:
        raise ResourceNotFound('Therapist')

    date_from = request.args.get('dateFrom')
    date_to = request.args.get('dateTo')

    if not date_from or not date_to:
        raise ValidationError('dateFrom and dateTo are required')

    schedule = TherapistService.get_schedule(therapist_id, date_from, date_to)

    return success_response({
        'therapistId': therapist_id,
        'name': therapist.name,
        'schedule': schedule
    })
