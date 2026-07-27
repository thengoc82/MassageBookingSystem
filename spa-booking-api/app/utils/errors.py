from flask import jsonify


class APIError(Exception):
    status_code = 400

    def __init__(self, code, message, status_code=None):
        super().__init__()
        self.code = code
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        return {
            'success': False,
            'error': {
                'code': self.code,
                'message': self.message
            }
        }

class ValidationError(APIError):
    def __init__(self, message='Invalid or missing input data'):
        super().__init__('VALIDATION_ERROR', message, 400)

class ResourceNotFound(APIError):
    def __init__(self, resource='Resource'):
        super().__init__('RESOURCE_NOT_FOUND', f'{resource} not found', 404)

class BusinessRuleViolation(APIError):
    def __init__(self, code, message):
        super().__init__(code, message, 422)

class Unauthorized(APIError):
    def __init__(self, message='Authentication required'):
        super().__init__('UNAUTHORIZED', message, 401)

class Forbidden(APIError):
    def __init__(self, message='No permission'):
        super().__init__('FORBIDDEN', message, 403)

def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'RESOURCE_NOT_FOUND',
                'message': 'Resource not found'
            }
        }), 404

    @app.errorhandler(500)
    def handle_500(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'Unexpected server error'
            }
        }), 500
