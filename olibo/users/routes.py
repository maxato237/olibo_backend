from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from olibo import db
from olibo.common.enums import UserRole
from olibo.common.helpers import get_authorized_user
from olibo.users.model import User

users = Blueprint('users', __name__)


# ==========================================
# USER ROUTES
# ==========================================


@users.route('/create', methods=['POST'])
@jwt_required()
def create_user():
    try:
        current_user = get_authorized_user()

        if current_user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Only super admin or admin can create users'}), 403

        data = request.get_json()

        if not all(k in data for k in ['email', 'password', 'first_name', 'last_name', 'role']):
            return jsonify({'error': 'Missing required fields: email, password, first_name, last_name, role'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409

        role = data['role']['value'] if isinstance(data['role'], dict) else data['role']
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            return jsonify({'error': f'Invalid role. Allowed: {valid_roles}'}), 400

        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone', ''),
            role=role,
            is_active=data.get('is_active', True),
            password_hash=generate_password_hash(data['password']),
        )

        db.session.add(user)
        db.session.commit()

        return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users.route('', methods=['GET'])
@jwt_required()
def get_all_users():
    try:
        current_user = get_authorized_user()

        if current_user.role not in ['super_admin', 'admin_competition', 'operator', 'team_manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        role = request.args.get('role')
        is_active = request.args.get('is_active')

        query = User.query
        if role:
            query = query.filter_by(role=role)
        if is_active is not None:
            query = query.filter_by(is_active=is_active.lower() == 'true')

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'message': 'Users retrieved successfully',
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages,
            'per_page': per_page,
            'users': [u.to_dict() for u in pagination.items],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@users.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    try:
        current_user = get_authorized_user()

        if current_user.id != user_id and current_user.role not in ['super_admin', 'admin_competition', 'team_manager']:
            return jsonify({'error': 'Unauthorized'}), 403

        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'User retrieved successfully', 'user': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@users.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        current_user = get_authorized_user()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if current_user.id != user_id and current_user.role != 'super_admin':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already exists'}), 409
            user.email = data['email']
        if 'password' in data:
            if current_user.role != 'super_admin':
                old_password = data.get('old_password')
                if not old_password or not check_password_hash(user.password_hash, old_password):
                    return jsonify({'error': 'Current password is required and must be correct'}), 400
            user.password_hash = generate_password_hash(data['password'])
        if 'role' in data and current_user.role == 'super_admin':
            role_value = data['role']['value'] if isinstance(data['role'], dict) else data['role']
            valid_roles = [r.value for r in UserRole]
            if role_value not in valid_roles:
                return jsonify({'error': f'Invalid role. Allowed: {valid_roles}'}), 400
            user.role = role_value
        if 'is_active' in data and current_user.role == 'super_admin':
            user.is_active = data['is_active']

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'User updated successfully', 'user': user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        current_user = get_authorized_user()

        if current_user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can delete users'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if current_user.id == user_id:
            return jsonify({'error': 'You cannot delete your own account'}), 400

        db.session.delete(user)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users.route('/<int:user_id>/deactivate', methods=['POST'])
@jwt_required()
def deactivate_user(user_id):
    try:
        current_user = get_authorized_user()

        if current_user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can deactivate users'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if current_user.id == user_id:
            return jsonify({'error': 'You cannot deactivate your own account'}), 400

        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'User deactivated successfully', 'user': user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users.route('/<int:user_id>/activate', methods=['POST'])
@jwt_required()
def activate_user(user_id):
    try:
        current_user = get_authorized_user()

        if current_user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can activate users'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'User activated successfully', 'user': user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
