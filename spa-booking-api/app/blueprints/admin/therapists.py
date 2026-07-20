from flask import request
from app.blueprints.admin import admin_bp
from app.utils.decorators import role_required
from app.models.therapist import Therapist
from app.models.shop import Shop
from app.models.user import User
from app.extensions import db
from app.utils import success_response, paginated_response
from app.utils.errors import ResourceNotFound, ValidationError

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
        username=data['username'],
        password=data['password']
    )
    
    db.session.add(therapist)
    db.session.commit()
    
    return success_response({'therapistId': therapist.id}, message='Therapist created', status_code=201)
