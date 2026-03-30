from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from olibo import db
from olibo.competition.model import Competition
from olibo.users.model import User


competition = Blueprint('competition', __name__)


# Create competition
@competition.route('', methods=['POST'])
@jwt_required()
def create_competition():
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if not all(k in data for k in ['name', 'start_date', 'end_date', 'season']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        competition = Competition(
            name=data['name'],
            description=data.get('description'),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            season=data['season']
        )
        
        db.session.add(competition)
        db.session.commit()
        
        return jsonify({
            'message': 'Competition created successfully',
            'competition': competition.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all competitions
@competition.route('', methods=['GET'])
def get_all_competitions():
    try:
        competitions = Competition.query.all()
        
        return jsonify({
            'message': 'Competitions retrieved successfully',
            'total': len(competitions),
            'competitions': [c.to_dict() for c in competitions]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get competition by ID
@competition.route('/<int:comp_id>', methods=['GET'])
def get_competition(comp_id):
    try:
        competition = Competition.query.get(comp_id)
        
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404
        
        return jsonify({
            'message': 'Competition retrieved successfully',
            'competition': competition.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update competition
@competition.route('/<int:comp_id>', methods=['PUT'])
@jwt_required()
def update_competition(comp_id):
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        competition = Competition.query.get(comp_id)
        
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            competition.name = data['name']
        if 'description' in data:
            competition.description = data['description']
        if 'start_date' in data:
            competition.start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            competition.end_date = datetime.fromisoformat(data['end_date'])
        if 'is_active' in data:
            competition.is_active = data['is_active']
        
        competition.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Competition updated successfully',
            'competition': competition.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete competition
@competition.route('/<int:comp_id>', methods=['DELETE'])
@jwt_required()
def delete_competition(comp_id):
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can delete competitions'}), 403
        
        competition = Competition.query.get(comp_id)
        
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404
        
        db.session.delete(competition)
        db.session.commit()
        
        return jsonify({'message': 'Competition deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
