from flask import request
from flask_jwt_extended import get_jwt_identity

from app.blueprints.admin import admin_bp
from app.services.customer_restriction_service import CustomerRestrictionService
from app.utils import paginated_response, success_response
from app.utils.decorators import role_required
from app.utils.errors import ValidationError


@admin_bp.route('/customer-restrictions', methods=['GET'])
@role_required('admin')
def list_customer_restrictions():
    try:
        page = int(request.args.get('page', '1'))
        size = int(request.args.get('size', '20'))
    except ValueError as error:
        raise ValidationError('page and size must be integers') from error
    data, pagination = CustomerRestrictionService.list(
        request.args.get('phone'), request.args.get('status', 'active'), page, size)
    return paginated_response(data, page, size, pagination['total'])


@admin_bp.route('/customer-restrictions', methods=['POST'])
@role_required('admin')
def create_customer_restriction():
    identity = get_jwt_identity()
    actor = identity.get('username') or str(identity.get('user_id') or 'admin')
    item = CustomerRestrictionService.create(request.get_json(silent=True), actor)
    return success_response(item, message='Customer blocked', status_code=201)


@admin_bp.route('/customer-restrictions/<int:restriction_id>', methods=['GET'])
@role_required('admin')
def get_customer_restriction(restriction_id):
    return success_response(CustomerRestrictionService.get(restriction_id))


@admin_bp.route('/customer-restrictions/<int:restriction_id>', methods=['PATCH'])
@role_required('admin')
def update_customer_restriction(restriction_id):
    item = CustomerRestrictionService.update(restriction_id, request.get_json(silent=True))
    return success_response(item, message='Customer restriction updated')


@admin_bp.route('/customer-restrictions/<int:restriction_id>', methods=['DELETE'])
@role_required('admin')
def delete_customer_restriction(restriction_id):
    return success_response({'restrictionId': CustomerRestrictionService.delete(restriction_id)},
                            message='Customer unblocked')
