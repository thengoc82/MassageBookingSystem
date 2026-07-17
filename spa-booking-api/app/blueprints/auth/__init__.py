from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from app.models.user import User
from app.utils import success_response
from app.utils.errors import ValidationError, Unauthorized

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        raise ValidationError('Username and password required')
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        raise Unauthorized('Invalid username or password')
    
    if not user.is_active:
        raise Unauthorized('Account is inactive')
    
    access_token = create_access_token(identity={
        'user_id': user.id,
        'username': user.username,
        'role': user.role
    })
    
    return success_response({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    }, message='Login successful')
