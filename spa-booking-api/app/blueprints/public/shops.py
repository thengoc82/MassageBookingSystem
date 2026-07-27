from app.blueprints.public import public_bp
from app.models.shop import Shop
from app.utils import success_response
from app.utils.errors import ResourceNotFound


@public_bp.route('/shops', methods=['GET'])
def get_shops():
    shops = Shop.query.filter_by(status='Open').all()

    data = [{
        'shopId': shop.id,
        'shopName': shop.name,
        'address': shop.address,
        'phoneNumber': shop.phone_number,
        'status': shop.status,
        'openTime': shop.open_time.strftime('%H:%M'),
        'closeTime': shop.close_time.strftime('%H:%M')
    } for shop in shops]

    return success_response(data)

@public_bp.route('/shops/<int:shop_id>', methods=['GET'])
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
