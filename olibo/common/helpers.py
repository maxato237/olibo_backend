from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from olibo.users.model import User


def get_authorized_user():
    return User.query.get(get_jwt_identity())


def require_roles(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_authorized_user()
            if not user or user.role not in roles:
                return jsonify({'error': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
