from contextvars import Token
from datetime import timedelta
import re
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity
from flask_jwt_extended import jwt_required
from olibo import db
from olibo.users.model import User
from werkzeug.security import generate_password_hash,check_password_hash

auth = Blueprint('auth', __name__)

# Helper function for email validation
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Register
@auth.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validation
        if not data or not all(k in data for k in ['email', 'password', 'first_name', 'last_name', 'role']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not is_valid_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Check if user exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Create user
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

# Login
@auth.route('/login', methods=['POST'])
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
        
        # Create token
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'role': user.role,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Logout (invalidate token)
@auth.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete all tokens for this user
        Token.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Refresh token
@auth.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        new_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'role': user.role,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({'access_token': new_token}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth.route('/check-superadmin', methods=['GET'])
def check_superadmin():
    # try:
        superadmin = User.query.filter_by(role='super_admin').first()

        return jsonify({
            'exists': superadmin is not None,
            'message': 'Super admin existe' if superadmin else 'Aucun super admin trouvé'
        }), 200

    # except Exception as e:
    #     return jsonify({
    #         'error': str(e),
    #         'exists': False 
    #     }), 500


@auth.route('/setup-complete', methods=['POST'])
def setup_complete():
    """
    Endpoint pour vérifier que la configuration initiale est complète
    """
    try:
        # Vérifie que le super admin existe
        superadmin = User.query.filter_by(role='super_admin').first()

        if not superadmin:
            return jsonify({
                'error': 'Setup non complète - super admin manquant',
                'complete': False
            }), 400

        # Vérifie qu'il y a au moins un admin de compétition
        admin = User.query.filter_by(role='admin_competition').first()

        return jsonify({
            'complete': True,
            'has_admin_competition': admin is not None,
            'message': 'Configuration initiale complète'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500