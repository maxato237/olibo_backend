from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload
from olibo.common.helpers import get_authorized_user
from olibo.competition.model import Competition
from olibo.ranking.model import Ranking
from olibo.ranking.utilities import recalculate_rankings
from olibo.users.model import User

ranking = Blueprint('ranking', __name__)


# Get rankings by competition
@ranking.route('/competition/<int:comp_id>', methods=['GET'])
def get_competition_rankings(comp_id):
    try:
        competition = Competition.query.get(comp_id)

        if not competition:
            return jsonify({'error': 'Competition not found'}), 404

        rankings = (
            Ranking.query
            .filter_by(competition_id=comp_id)
            .options(joinedload(Ranking.team))
            .order_by(Ranking.position.nulls_last())
            .all()
        )

        def ranking_with_team(r):
            data = r.to_dict()
            data['team'] = {
                'id': r.team.id,
                'name': r.team.name,
                'logo': r.team.logo,
                'description': r.team.description,
                'representative_id': r.team.representative_id,
                'created_at': r.team.created_at.isoformat(),
                'updated_at': r.team.updated_at.isoformat(),
            }
            return data

        return jsonify({
            'message': 'Rankings retrieved successfully',
            'total': len(rankings),
            'rankings': [ranking_with_team(r) for r in rankings]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get ranking for a specific team in a competition
@ranking.route('/competition/<int:comp_id>/team/<int:team_id>', methods=['GET'])
def get_team_ranking(comp_id, team_id):
    try:
        competition = Competition.query.get(comp_id)
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404

        ranking = Ranking.query.filter_by(competition_id=comp_id, team_id=team_id).first()
        if not ranking:
            return jsonify({'message': 'No ranking found for this team', 'ranking': None}), 200

        return jsonify({'ranking': ranking.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Recalculate rankings manually
@ranking.route('', methods=['POST'])
@jwt_required()
def update_rankings():
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if 'competition_id' not in data:
            return jsonify({'error': 'competition_id is required'}), 400

        competition = Competition.query.get(data['competition_id'])
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404

        recalculate_rankings(data['competition_id'])

        rankings = Ranking.query.filter_by(
            competition_id=data['competition_id']
        ).order_by(Ranking.position.nulls_last()).all()

        return jsonify({
            'message': 'Rankings recalculated successfully',
            'rankings': [r.to_dict() for r in rankings]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
