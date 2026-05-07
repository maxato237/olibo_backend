from olibo.auth.model import Token
from datetime import timedelta
import re
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    get_jwt_identity, jwt_required
)
from olibo import db, limiter
from olibo.common.enums import UserRole
from olibo.users.model import User
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def _make_tokens(user):
    claims = {
        'role': user.role,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id))
    return access_token, refresh_token


# Register
@auth.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ['email', 'password', 'first_name', 'last_name', 'role']):
            return jsonify({'error': 'Missing required fields'}), 400

        if not is_valid_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        valid_roles = [r.value for r in UserRole]
        if data['role'] not in valid_roles:
            return jsonify({'error': f'Invalid role. Allowed: {valid_roles}'}), 400

        ALLOWED_SELF_REGISTER_ROLES = ['team_captain', 'team_manager', 'coach', 'spectator']
        if data['role'] not in ALLOWED_SELF_REGISTER_ROLES:
            return jsonify({'error': 'Invalid role for self-registration. Allowed: team_captain, team_manager, coach, spectator'}), 403

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409

        user = User(
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role=data['role']
        )

        db.session.add(user)
        db.session.commit()

        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Login — limité à 5 tentatives par minute
@auth.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ['telephone', 'password']):
            return jsonify({'error': 'Missing telephone or password'}), 400

        user = User.query.filter_by(phone=data['telephone']).first()

        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'User account is disabled'}), 403

        access_token, refresh_token = _make_tokens(user)

        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Logout
@auth.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        Token.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        return jsonify({'message': 'Logged out successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Refresh — utilise le refresh token dédié
@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        access_token, _ = _make_tokens(user)

        return jsonify({'access_token': access_token}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Profil de l'utilisateur connecté
@auth.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    try:
        user = User.query.get(get_jwt_identity())
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth.route('/check-superadmin', methods=['GET'])
def check_superadmin():
    try:
        superadmin = User.query.filter_by(role='super_admin').first()
        admin = User.query.filter_by(role='admin_competition').first()

        return jsonify({
            'exists': superadmin is not None,
            'admin_competition_exists': admin is not None,
            'message': 'Super admin existe' if superadmin else 'Aucun super admin trouvé'
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'exists': False
        }), 500


@auth.route('/setup-complete', methods=['GET'])
def setup_complete():
    try:
        superadmin = User.query.filter_by(role='super_admin').first()

        if not superadmin:
            return jsonify({
                'error': 'Setup non complète - super admin manquant',
                'complete': False
            }), 400

        admin = User.query.filter_by(role='admin_competition').first()

        return jsonify({
            'complete': True,
            'has_admin_competition': admin is not None,
            'message': 'Configuration initiale complète'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
