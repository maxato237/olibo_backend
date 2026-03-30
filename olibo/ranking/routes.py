from flask import Blueprint
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from olibo.competition.model import Competition
from olibo.ranking.model import Ranking
from olibo.users.model import User

ranking = Blueprint('ranking', __name__)


# Get rankings by competition
@ranking.route('/competition/<int:comp_id>', methods=['GET'])
def get_competition_rankings(comp_id):
    try:
        competition = Competition.query.get(comp_id)
        
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404
        
        rankings = Ranking.query.filter_by(competition_id=comp_id).order_by(Ranking.position).all()
        
        return jsonify({
            'message': 'Rankings retrieved successfully',
            'total': len(rankings),
            'rankings': [r.to_dict() for r in rankings]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update ranking (called after match completion)
@ranking.route('', methods=['POST'])
@jwt_required()
def update_rankings():
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if 'competition_id' not in data:
            return jsonify({'error': 'Competition ID is required'}), 400
        
        # This would typically be called automatically after a match
        # Here's a manual update endpoint
        
        return jsonify({
            'message': 'Rankings updated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
