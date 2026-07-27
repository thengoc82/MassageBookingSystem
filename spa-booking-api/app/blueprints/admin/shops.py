from app.blueprints.admin import admin_bp
from app.extensions import db
from app.models.shop import Shop
from app.utils import paginated_response, success_response
from app.utils.decorators import role_required
from app.utils.errors import ResourceNotFound, ValidationError
from flask import request


@admin_bp.route('/shops', methods=['GET'])
@role_required('admin')
def get_shops():
    status = request.args.get('status', 'All')
    page = request.args.get('page', type=int, default=1)
    size = request.args.get('size', type=int, default=20)

    query = Shop.query

    if status != 'All':
        query = query.filter_by(status=status)

    total = query.count()
    shops = query.offset((page - 1) * size).limit(size).all()

    data = [{
        'shopId': shop.id,
        'shopName': shop.name,
        'address': shop.address,
        'phoneNumber': shop.phone_number,
        'status': shop.status,
        'openTime': shop.open_time.strftime('%H:%M'),
        'closeTime': shop.close_time.strftime('%H:%M')
    } for shop in shops]

    return paginated_response(data, page, size, total)

@admin_bp.route('/shops', methods=['POST'])
@role_required('admin')
def create_shop():
    data = request.get_json()

    if not data.get('shopName'):
        raise ValidationError('shopName is required')

    if not data.get('address'):
        raise ValidationError('address is required')

    if not data.get('phoneNumber'):
        raise ValidationError('phoneNumber is required')

    shop = Shop(
        name=data['shopName'],
        address=data['address'],
        phone_number=data['phoneNumber'],
        open_time=data.get('openTime', '08:00'),
        close_time=data.get('closeTime', '21:00')
    )

    db.session.add(shop)
    db.session.commit()

    return success_response({'shopId': shop.id}, message='Shop created', status_code=201)

@admin_bp.route('/shops/<int:shop_id>', methods=['GET'])
@role_required('admin')
def get_shop(shop_id):
    shop = Shop.query.get(shop_id)

    if not shop:
        raise ResourceNotFound('Shop')

    data = {
        'shopId': shop.id,
        'shopName': shop.name,
        'address': shop.address,
        'phoneNumber': shop.phone_number,
        'status': shop.status,
        'openTime': shop.open_time.strftime('%H:%M'),
        'closeTime': shop.close_time.strftime('%H:%M')
    }

    return success_response(data)

@admin_bp.route('/shops/<int:shop_id>', methods=['PATCH'])
@role_required('admin')
def update_shop(shop_id):
    shop = Shop.query.get(shop_id)

    if not shop:
        raise ResourceNotFound('Shop')

    data = request.get_json()

    if 'shopName' in data:
        shop.name = data['shopName']
    if 'address' in data:
        shop.address = data['address']
    if 'status' in data:
        shop.status = data['status']
    if 'openTime' in data:
        shop.open_time = data['openTime']
    if 'closeTime' in data:
        shop.close_time = data['closeTime']

    db.session.commit()

    return success_response({'shopId': shop.id}, message='Shop updated')
