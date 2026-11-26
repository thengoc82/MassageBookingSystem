from app.blueprints.admin import admin_bp
from app.models.customer import Customer
from app.services.customer_service import CustomerService
from app.utils import success_response
from app.utils.decorators import role_required
from app.utils.errors import ResourceNotFound
from flask import request


@admin_bp.route('/customers', methods=['GET'])
@role_required('admin')
def list_customers():
    query = Customer.query

    phone = request.args.get('phone')
    if phone:
        query = query.filter_by(phone_number=phone)

    customers = query.order_by(Customer.created_at.desc()).all()
    blocked = request.args.get('blocked')
    data = []
    for customer in customers:
        is_blocked = CustomerService.check_eligibility(customer.phone_number)['isBlocked']
        if blocked in ('true', 'false') and is_blocked != (blocked == 'true'):
            continue
        data.append({
            'customerId': customer.id,
            'phoneNumber': customer.phone_number,
            'memberRank': customer.member_rank,
            'visitCount': customer.visit_count,
            'isBlocked': is_blocked,
            'createdAt': customer.created_at.strftime('%Y-%m-%d') if customer.created_at else None
        })

    return success_response(data)


@admin_bp.route('/customers/<int:customer_id>', methods=['GET'])
@role_required('admin')
def get_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        raise ResourceNotFound('Customer')

    data = {
        'customerId': customer.id,
        'phoneNumber': customer.phone_number,
        'memberRank': customer.member_rank,
        'visitCount': customer.visit_count,
        'isBlocked': CustomerService.check_eligibility(customer.phone_number)['isBlocked'],
        'createdAt': customer.created_at.strftime('%Y-%m-%d') if customer.created_at else None
    }

    return success_response(data)
