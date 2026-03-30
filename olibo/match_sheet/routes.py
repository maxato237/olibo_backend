from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from olibo import db
from olibo.common.enums import MatchStatus
from olibo.competition.model import Competition
from olibo.match_sheet.model import Match, MatchEvent, MatchSheet  # ← import corrigé
from olibo.team.model import TeamMember, Team                       # ← Player → TeamMember
from olibo.users.model import User

match_sheet = Blueprint('match_sheet', __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_authorized_user() -> User:
    return User.query.get(get_jwt_identity())


# ==========================================
# MATCH ROUTES
# ==========================================


@match_sheet.route('/matches', methods=['POST'])
@jwt_required()
def create_match():
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        if not all(k in data for k in ['competition_id', 'home_team_id', 'away_team_id', 'scheduled_date']):
            return jsonify({'error': 'Missing required fields'}), 400

        if data['home_team_id'] == data['away_team_id']:
            return jsonify({'error': 'Teams must be different'}), 400

        if not Competition.query.get(data['competition_id']):
            return jsonify({'error': 'Competition not found'}), 404

        if not Team.query.get(data['home_team_id']) or not Team.query.get(data['away_team_id']):
            return jsonify({'error': 'One or both teams not found'}), 404

        match = Match(
            competition_id=data['competition_id'],
            home_team_id=data['home_team_id'],
            away_team_id=data['away_team_id'],
            scheduled_date=datetime.fromisoformat(data['scheduled_date']),
            matchday=data.get('matchday'),
            location=data.get('location'),
            referee_id=data.get('referee_id'),
        )

        db.session.add(match)
        db.session.commit()

        return jsonify({'message': 'Match created successfully', 'match': match.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches', methods=['GET'])
def get_all_matches():
    try:
        competition_id = request.args.get('competition_id', type=int)
        status = request.args.get('status')

        query = Match.query
        if competition_id:
            query = query.filter_by(competition_id=competition_id)
        if status:
            query = query.filter_by(status=status)

        matches = query.all()

        return jsonify({
            'message': 'Matches retrieved successfully',
            'total': len(matches),
            'matches': [m.to_dict() for m in matches],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/<int:match_id>', methods=['GET'])
def get_match(match_id):
    try:
        match = Match.query.get(match_id)

        if not match:
            return jsonify({'error': 'Match not found'}), 404

        return jsonify({'message': 'Match retrieved successfully', 'match': match.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
# MATCH SHEET ROUTES
# ==========================================


@match_sheet.route('/matches/<int:match_id>/sheet', methods=['POST'])
@jwt_required()
def fill_match_sheet(match_id):
    try:
        user = get_authorized_user()

        if user.role not in ['referee', 'commissioner']:
            return jsonify({'error': 'Only referees or commissioners can fill match sheets'}), 403

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        data = request.get_json()

        existing_sheet = MatchSheet.query.filter_by(match_id=match_id).first()

        if existing_sheet:
            existing_sheet.filled_by_id = user.id
            existing_sheet.notes = data.get('notes')
            existing_sheet.filled_at = datetime.utcnow()
            sheet = existing_sheet
        else:
            sheet = MatchSheet(
                match_id=match_id,
                filled_by_id=user.id,
                notes=data.get('notes'),
            )
            db.session.add(sheet)

        if 'home_team_goals' in data:
            match.home_team_goals = data['home_team_goals']
        if 'away_team_goals' in data:
            match.away_team_goals = data['away_team_goals']

        match.status = MatchStatus.COMPLETED.value

        db.session.commit()

        return jsonify({'message': 'Match sheet filled successfully', 'sheet': sheet.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/<int:match_id>/sheet/validate', methods=['POST'])
@jwt_required()
def validate_match_sheet(match_id):
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        sheet = MatchSheet.query.filter_by(match_id=match_id).first()
        if not sheet:
            return jsonify({'error': 'Match sheet not found'}), 404

        sheet.is_validated = True
        sheet.validated_by_id = user.id
        sheet.validated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({'message': 'Match sheet validated successfully', 'sheet': sheet.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==========================================
# MATCH EVENT ROUTES
# ==========================================


@match_sheet.route('/matches/<int:match_id>/events', methods=['POST'])
@jwt_required()
def add_match_event(match_id):
    try:
        user = get_authorized_user()

        if user.role not in ['referee', 'commissioner']:
            return jsonify({'error': 'Unauthorized'}), 403

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        data = request.get_json()

        # ── Validation des champs obligatoires ────────────────────────────
        if not all(k in data for k in ['member_id', 'event_type', 'minute']):
            return jsonify({'error': 'Missing required fields: member_id, event_type, minute'}), 400

        # ── Vérification que le membre appartient à l'un des deux clubs ───
        member = TeamMember.query.get(data['member_id'])

        if not member or member.team_id not in (match.home_team_id, match.away_team_id):
            return jsonify({'error': 'Member not part of this match'}), 404

        # ── Seuls les joueurs peuvent générer des buts, cartons, etc. ─────
        non_player_events = {'substitution'}  # élargir si besoin
        if not member.is_player and data['event_type'] not in non_player_events:
            return jsonify({'error': f"Non-player members can only have event type: {non_player_events}"}), 400

        event = MatchEvent(
            match_id=match_id,
            member_id=data['member_id'],   # ← renommé depuis player_id
            event_type=data['event_type'],
            minute=data['minute'],
            card_type=data.get('card_type'),
            notes=data.get('notes'),
        )

        db.session.add(event)
        db.session.commit()

        return jsonify({'message': 'Match event added successfully', 'event': event.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/<int:match_id>/events', methods=['GET'])
def get_match_events(match_id):
    try:
        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()

        return jsonify({
            'message': 'Match events retrieved successfully',
            'total': len(events),
            'events': [e.to_dict() for e in events],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500