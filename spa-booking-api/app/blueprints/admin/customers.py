from app.blueprints.admin import admin_bp
from app.models.customer import Customer
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

    blocked = request.args.get('blocked')
    if blocked == 'true':
        query = query.filter_by(is_blocked=True)
    elif blocked == 'false':
        query = query.filter_by(is_blocked=False)

    customers = query.order_by(Customer.created_at.desc()).all()

    data = [{
        'customerId': c.id,
        'phoneNumber': c.phone_number,
        'memberRank': c.member_rank,
        'visitCount': c.visit_count,
        'isBlocked': c.is_blocked,
        'createdAt': c.created_at.strftime('%Y-%m-%d') if c.created_at else None
    } for c in customers]

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
        'isBlocked': customer.is_blocked,
        'createdAt': customer.created_at.strftime('%Y-%m-%d') if customer.created_at else None
    }

    return success_response(data)
