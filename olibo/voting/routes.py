from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from olibo import db
from olibo.common.enums import VoteType
from olibo.common.helpers import get_authorized_user
from olibo.competition.model import Competition
from olibo.team.model import TeamMember
from olibo.users.model import User
from olibo.voting.model import Vote, VoteResult

voting = Blueprint('voting', __name__)


# ==========================================
# VOTING ROUTES
# ==========================================


@voting.route('', methods=['POST'])
@jwt_required()
def cast_vote():
    try:
        voter_id = get_jwt_identity()
        data = request.get_json()

        if not all(k in data for k in ['member_id', 'competition_id', 'vote_type']):
            return jsonify({'error': 'Missing required fields: member_id, competition_id, vote_type'}), 400

        valid_vote_types = [v.value for v in VoteType]
        if data['vote_type'] not in valid_vote_types:
            return jsonify({'error': f"Invalid vote_type. Allowed: {valid_vote_types}"}), 400

        if data['vote_type'] == VoteType.PLAYER_OF_DAY.value and not data.get('matchday'):
            return jsonify({'error': 'matchday is required for player_of_day votes'}), 400

        member = TeamMember.query.get(data['member_id'])
        competition = Competition.query.get(data['competition_id'])

        if not member:
            return jsonify({'error': 'Member not found'}), 404
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404

        if not competition.is_active:
            return jsonify({'error': 'Voting is only allowed for active competitions'}), 400

        if not member.is_player:
            return jsonify({'error': 'You can only vote for players'}), 400

        existing_vote = Vote.query.filter_by(
            voter_id=voter_id,
            vote_type=data['vote_type'],
            competition_id=data['competition_id'],
            matchday=data.get('matchday'),
        ).first()

        if existing_vote:
            return jsonify({'error': 'You have already voted in this category for this period'}), 409

        vote = Vote(
            voter_id=voter_id,
            member_id=data['member_id'],
            competition_id=data['competition_id'],
            vote_type=data['vote_type'],
            matchday=data.get('matchday'),
        )
        db.session.add(vote)
        db.session.flush()

        result = VoteResult.query.filter_by(
            member_id=data['member_id'],
            competition_id=data['competition_id'],
            vote_type=data['vote_type'],
            matchday=data.get('matchday'),
        ).first()

        if result:
            result.vote_count += 1
            result.updated_at = datetime.utcnow()
        else:
            result = VoteResult(
                member_id=data['member_id'],
                competition_id=data['competition_id'],
                vote_type=data['vote_type'],
                matchday=data.get('matchday'),
                vote_count=1,
            )
            db.session.add(result)

        db.session.commit()

        return jsonify({'message': 'Vote cast successfully', 'vote': vote.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@voting.route('/results', methods=['GET'])
@jwt_required()
def get_vote_results():
    try:
        user = get_authorized_user()

        if user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can view vote results'}), 403

        competition_id = request.args.get('competition_id', type=int)
        vote_type = request.args.get('vote_type')
        matchday = request.args.get('matchday', type=int)

        query = VoteResult.query
        if competition_id:
            query = query.filter_by(competition_id=competition_id)
        if vote_type:
            query = query.filter_by(vote_type=vote_type)
        if matchday:
            query = query.filter_by(matchday=matchday)

        results = query.order_by(VoteResult.vote_count.desc()).all()

        return jsonify({
            'message': 'Vote results retrieved successfully',
            'total': len(results),
            'results': [r.to_dict() for r in results],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voting.route('/has-voted', methods=['GET'])
@jwt_required()
def has_voted():
    try:
        voter_id = get_jwt_identity()
        vote_type = request.args.get('vote_type')
        comp_id = request.args.get('competition_id', type=int)
        matchday = request.args.get('matchday', type=int)

        existing = Vote.query.filter_by(
            voter_id=voter_id,
            vote_type=vote_type,
            competition_id=comp_id,
            matchday=matchday
        ).first()

        return jsonify({'has_voted': existing is not None}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voting.route('/<int:vote_id>', methods=['DELETE'])
@jwt_required()
def delete_vote(vote_id):
    try:
        user = get_authorized_user()

        if user.role != 'super_admin':
            return jsonify({'error': 'Only super admin can delete votes'}), 403

        vote = Vote.query.get(vote_id)
        if not vote:
            return jsonify({'error': 'Vote not found'}), 404

        result = VoteResult.query.filter_by(
            member_id=vote.member_id,
            competition_id=vote.competition_id,
            vote_type=vote.vote_type,
            matchday=vote.matchday,
        ).first()

        if result:
            result.vote_count = max(0, result.vote_count - 1)
            result.updated_at = datetime.utcnow()
            if result.vote_count <= 0:
                db.session.delete(result)

        db.session.delete(vote)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
