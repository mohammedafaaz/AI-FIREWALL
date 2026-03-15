from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from database import models


def jwt_required_middleware(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'data': None,
                'error': 'Authentication required',
                'module': 'AUTH',
                'timestamp': ''
            }), 401
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            user = models.get_user_by_id(int(identity))
            if not user or user['role'] not in ['admin', 'hr']:
                return jsonify({
                    'success': False,
                    'data': None,
                    'error': 'Admin access required',
                    'module': 'AUTH',
                    'timestamp': ''
                }), 403
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'data': None,
                'error': str(e),
                'module': 'AUTH',
                'timestamp': ''
            }), 401
    return decorated