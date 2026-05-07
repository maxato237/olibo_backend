from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy.orm import joinedload
from olibo import db
from olibo.common.helpers import get_authorized_user
from olibo.common.enums import CompetitionType
from olibo.competition.model import Competition
from olibo.match_sheet.model import Match
from olibo.ranking.model import Ranking
from olibo.users.model import User
from olibo.season.model import Season


competition = Blueprint('competition', __name__)


# Get active competition
@competition.route('/active', methods=['GET'])
def get_active_competition():
    try:
        comp = Competition.query.filter_by(is_active=True).first()
        if not comp:
            return jsonify({'message': 'No active competition', 'competition': None}), 200
        return jsonify({'competition': comp.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Create competition
@competition.route('', methods=['POST'])
@jwt_required()
def create_competition():
    # try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if not all(k in data for k in ['name', 'start_date', 'end_date', 'season', 'competition_type']):
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            competition_type = CompetitionType(data['competition_type'])
        except ValueError:
            return jsonify({'error': 'Invalid competition_type value'}), 400

        start = datetime.fromisoformat(data['start_date'])
        end = datetime.fromisoformat(data['end_date'])
        if end <= start:
            return jsonify({'error': 'end_date must be after start_date'}), 400

        if Competition.query.filter_by(season=data['season']).first():
            return jsonify({'error': f"A competition for season {data['season']} already exists"}), 409

        if data.get('is_active', False):
            Competition.query.update({'is_active': False})

        comp = Competition(
            name=data['name'],
            description=data.get('description'),
            start_date=start,
            end_date=end,
            season_id=data['season_id'],
            season=data['season'],
            is_active=data.get('is_active', False),
            competition_type=competition_type,
            **({'ranking_rules': data['ranking_rules']} if 'ranking_rules' in data else {}),
        )

        db.session.add(comp)
        db.session.commit()

        return jsonify({
            'message': 'Competition created successfully',
            'competition': comp.to_dict()
        }), 201

    # except Exception as e:
    #     db.session.rollback()
    #     return jsonify({'error': str(e)}), 500


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
        comp = Competition.query.get(comp_id)

        if not comp:
            return jsonify({'error': 'Competition not found'}), 404

        return jsonify({
            'message': 'Competition retrieved successfully',
            'competition': comp.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Update competition
@competition.route('/<int:comp_id>', methods=['PUT'])
@jwt_required()
def update_competition(comp_id):
    # try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        comp = Competition.query.get(comp_id)
        season = Season.query.filter_by(id = comp.season_id).first().to_dict()
        
        if not comp:
            return jsonify({'error': 'Competition not found'}), 404

        data = request.get_json()

        if 'name' in data:
            comp.name = data['name']
        if 'description' in data:
            comp.description = data['description']
        if 'start_date' in data:
            comp.start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            comp.end_date = datetime.fromisoformat(data['end_date'])
        if 'season' in data:
            comp.season = data['season']
        if 'season_id' in data :
            comp.season_id = data['season_id']
        if 'is_active' in data:
            if season['is_active'] or (not season['is_active'] and not data['is_active']):
                comp.is_active = data['is_active']
            else:
                return jsonify({'error': 'Season inactive'} ), 400
        if 'competition_type' in data:
            try:
                comp.competition_type = CompetitionType(data['competition_type'])
            except ValueError:
                return jsonify({'error': 'Invalid competition_type value'}), 400
        if 'ranking_rules' in data:
            comp.ranking_rules = data['ranking_rules']

        comp.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Competition updated successfully',
            'competition': comp.to_dict()
        }), 200

    # except Exception as e:
    #     db.session.rollback()
    #     return jsonify({'error': str(e)}), 500


# Delete competition
@competition.route('/<int:comp_id>', methods=['DELETE'])
@jwt_required()
def delete_competition(comp_id):
    try:
        user = get_authorized_user()

        if user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can delete competitions'}), 403

        comp = Competition.query.get(comp_id)

        if not comp:
            return jsonify({'error': 'Competition not found'}), 404

        played_matches = Match.query.filter_by(
            competition_id=comp_id,
            status='completed'
        ).count()

        if played_matches > 0:
            return jsonify({
                'error': f'Cannot delete a competition with {played_matches} played matches. Archive it instead.'
            }), 409

        db.session.delete(comp)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
