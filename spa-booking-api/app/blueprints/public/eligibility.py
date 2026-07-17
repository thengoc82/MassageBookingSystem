from flask import request
from app.blueprints.public import public_bp
from app.services.customer_service import CustomerService
from app.utils import success_response
from app.utils.errors import ValidationError

@public_bp.route('/booking-eligibility-checks', methods=['POST'])
def check_eligibility():
    data = request.get_json()
    
    if not data or 'phoneNumber' not in data:
        raise ValidationError('phoneNumber is required')
    
    eligibility = CustomerService.check_eligibility(data['phoneNumber'])
    
    return success_response(eligibility)
