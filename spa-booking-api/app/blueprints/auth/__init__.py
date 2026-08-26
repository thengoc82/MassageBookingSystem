from app.models.customer import Customer
from app.models.therapist import Therapist
from app.models.user import User
from app.utils import success_response
from app.utils.errors import Unauthorized, ValidationError
from flask import Blueprint, request
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        raise ValidationError('Username and password required')

    user = User.query.filter_by(username=data['username']).first()

    if user and user.check_password(data['password']) and user.is_active:
        access_token = create_access_token(identity={
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'type': 'admin'
        })

        return success_response({
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'type': 'admin'
            }
        }, message='Login successful')

    therapist = Therapist.query.filter_by(username=data['username']).first()

    if therapist and therapist.check_password(data['password']) and therapist.status == 'active':
        access_token = create_access_token(identity={
            'user_id': therapist.id,
            'username': therapist.username or therapist.name,
            'role': 'therapist',
            'type': 'therapist'
        })

        return success_response({
            'access_token': access_token,
            'user': {
                'id': therapist.id,
                'username': therapist.username or therapist.name,
                'role': 'therapist',
                'type': 'therapist'
            }
        }, message='Login successful')
    
    customer = Customer.query.filter_by(username=data['username']).first()

    if customer and customer.check_password(data['password']):
        access_token = create_access_token(identity={
            'user_id': customer.id,
            'username': customer.username,
            'role': 'customer',
            'type': 'customer'
        })
        
        return success_response({
            'access_token': access_token,
            'user': {
                'id': customer.id,
                'username': customer.username,
                'role': 'customer',
                'type': 'customer'
            }
        }, message='Login successful')

    raise Unauthorized('Invalid username or password')
