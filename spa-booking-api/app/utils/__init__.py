from flask import jsonify

def success_response(data=None, message='Success', status_code=200):
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code

def paginated_response(data, page, size, total, message='Success'):
    return jsonify({
        'success': True,
        'data': data,
        'pagination': {
            'page': page,
            'size': size,
            'total': total,
            'totalPages': (total + size - 1) // size
        },
        'message': message
    }), 200
