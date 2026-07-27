from functools import wraps

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.utils.errors import Forbidden, ValidationError


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            identity = get_jwt_identity()
            if identity.get('role') not in roles:
                raise Forbidden('Insufficient permissions')
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def validate_json(*required_fields):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError('Request must be JSON')
            data = request.get_json()
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise ValidationError(f'Missing required fields: {", ".join(missing)}')
            return fn(*args, **kwargs)
        return wrapper
    return decorator
