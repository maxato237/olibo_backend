from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload
from olibo import db
from olibo.common.enums import MatchStatus
from olibo.common.helpers import get_authorized_user
from olibo.competition.model import Competition
from olibo.match_sheet.model import Match, MatchEvent, MatchSheet
from olibo.ranking.model import Ranking
from olibo.season.model import Season
from olibo.team.model import TeamMember, Team
from olibo.users.model import User

match_sheet = Blueprint('match_sheet', __name__)

VALID_EVENT_TYPES = {'goal', 'assist', 'yellow_card', 'red_card', 'substitution'}

# Fuseau horaire Afrique Centrale (WAT = UTC+1)
WAT = timezone(timedelta(hours=1))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def team_info(team):
    return {
        'id': team.id,
        'name': team.name,
        'logo': team.logo,
        'description': team.description,
        'representative_id': team.representative_id,
    }


def ranking_info(competition_id, team_id):
    r = Ranking.query.filter_by(competition_id=competition_id, team_id=team_id).first()
    if not r:
        return None
    return {
        'position': r.position,
        'matches_played': r.matches_played,
        'wins': r.wins,
        'draws': r.draws,
        'losses': r.losses,
        'goals_for': r.goals_for,
        'goals_against': r.goals_against,
        'goal_difference': r.goal_difference,
        'points': r.points,
    }


def match_full_dict(m):
    """Match enrichi avec équipes + classements."""
    data = m.to_dict()
    data['home_team'] = team_info(m.home_team)
    data['away_team'] = team_info(m.away_team)
    data['home_team_ranking'] = ranking_info(m.competition_id, m.home_team_id)
    data['away_team_ranking'] = ranking_info(m.competition_id, m.away_team_id)
    return data


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

        competition = Competition.query.get(data['competition_id'])
        if not competition:
            return jsonify({'error': 'Competition not found'}), 404

        if not Team.query.get(data['home_team_id']) or not Team.query.get(data['away_team_id']):
            return jsonify({'error': 'One or both teams not found'}), 404

        season_id = data.get('season_id') or competition.season_id

        match = Match(
            competition_id=data['competition_id'],
            season_id=season_id,
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
    """Filtre simple : competition_id, status. Inchangé."""
    try:
        competition_id = request.args.get('competition_id', type=int)
        season_id = request.args.get('season_id', type=int)
        status = request.args.get('status')

        query = Match.query.options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
        )
        if competition_id:
            query = query.filter_by(competition_id=competition_id)
        if season_id:
            query = query.filter_by(season_id=season_id)
        if status:
            query = query.filter_by(status=status)

        matches = query.all()

        return jsonify({
            'message': 'Matches retrieved successfully',
            'total': len(matches),
            'matches': [match_full_dict(m) for m in matches],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/<int:match_id>', methods=['GET'])
def get_match(match_id):
    try:
        match = Match.query.options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
        ).get(match_id)

        if not match:
            return jsonify({'error': 'Match not found'}), 404

        return jsonify({'message': 'Match retrieved successfully', 'match': match_full_dict(match)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/<int:match_id>', methods=['PUT'])
@jwt_required()
def update_match(match_id):
    try:
        user = get_authorized_user()

        if user.role not in ['super_admin', 'admin_competition', 'operator']:
            return jsonify({'error': 'Unauthorized'}), 403

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        if match.status == MatchStatus.COMPLETED.value:
            return jsonify({'error': 'Cannot modify a completed match'}), 409

        data = request.get_json()

        if 'scheduled_date' in data:
            match.scheduled_date = datetime.fromisoformat(data['scheduled_date'])
        if 'location' in data:
            match.location = data['location']
        if 'matchday' in data:
            match.matchday = data['matchday']
        if 'referee_id' in data:
            match.referee_id = data['referee_id']

        db.session.commit()

        return jsonify({'message': 'Match updated successfully', 'match': match.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==========================================
# ROUTES SPÉCIALISÉES
# ==========================================


@match_sheet.route('/teams/<int:team_id>/matches', methods=['GET'])
def get_team_matches(team_id):
    """
    Tous les matches d'une équipe (domicile + extérieur).
    Paramètre optionnel : period = upcoming | past
    """
    try:
        period = request.args.get('period')

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        query = Match.query.options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
        ).filter(
            db.or_(
                Match.home_team_id == team_id,
                Match.away_team_id == team_id,
            )
        )

        if period == 'upcoming':
            query = query.filter(Match.scheduled_date >= now_utc)\
                         .order_by(Match.scheduled_date.asc())
        elif period == 'past':
            query = query.filter(Match.scheduled_date < now_utc)\
                         .order_by(Match.scheduled_date.desc())
        else:
            query = query.order_by(Match.scheduled_date.asc())

        matches = query.all()

        return jsonify({
            'message': 'Team matches retrieved successfully',
            'team_id': team_id,
            'period': period,
            'total': len(matches),
            'matches': [match_full_dict(m) for m in matches],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/teams/<int:team_id>/matches/current-season', methods=['GET'])
def get_team_matches_current_season(team_id):
    # try:
        if not Team.query.get(team_id):
            return jsonify({'error': 'Team not found'}), 404

        active_season = Season.query.filter_by(is_active=True).first()
        if not active_season:
            return jsonify({'error': 'No active season found'}), 404

        competition_id = request.args.get('competition_id', type=int)
        period = request.args.get('period')
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        # ── 1. Matchs ────────────────────────────────────────────────────────
        query = Match.query.options(
            joinedload(Match.home_team),   
            joinedload(Match.away_team),   
            joinedload(Match.competition),
        ).join(Competition).filter(       
            Competition.season_id == active_season.id, 
            db.or_(
                Match.home_team_id == team_id,
                Match.away_team_id == team_id,
            )
        )

        if competition_id:
            query = query.filter(Match.competition_id == competition_id)

        if period == 'upcoming':
            query = query.filter(Match.scheduled_date >= now_utc).order_by(Match.scheduled_date.asc())
        elif period == 'past':
            query = query.filter(Match.scheduled_date < now_utc).order_by(Match.scheduled_date.desc())
        else:
            query = query.order_by(Match.scheduled_date.asc())

        matches = query.all()

        # ── 2. Compétitions dédupliquées ─────────────────────────────────────
        seen_comp_ids = set()
        competitions = []
        for m in matches:
            if m.competition and m.competition_id not in seen_comp_ids:
                seen_comp_ids.add(m.competition_id)
                competitions.append(m.competition.to_dict())

        # ── 3. Rankings ──────────────────────────────────────────────────────
        all_team_ids = {m.home_team_id for m in matches} | {m.away_team_id for m in matches}
        comp_ids = {m.competition_id for m in matches}

        rankings_raw = (
            Ranking.query
            .options(joinedload(Ranking.competition)) 
            .join(Competition, Ranking.competition_id == Competition.id)
            .filter(
                Ranking.competition_id.in_(comp_ids),
                Ranking.team_id.in_(all_team_ids),
            )
            .all()
        ) if comp_ids and all_team_ids else []

        rankings_cache = {
            (r.competition_id, r.team_id): {
                'position': r.position,
                'matches_played': r.matches_played,
                'wins': r.wins,
                'draws': r.draws,
                'losses': r.losses,
                'goals_for': r.goals_for,
                'goals_against': r.goals_against,
                'goal_difference': r.goal_difference,
                'points': r.points,
            }
            for r in rankings_raw
        }

        team_rankings = [
            {
                **r.to_dict(),
                'competition': r.competition.to_dict() if r.competition else None,
            }
            for r in rankings_raw if r.team_id == team_id
        ]

        # ── 4. Sérialisation ─────────────────────────────────────────────────
        def _match_dict(m):
            data = m.to_dict()
            data['home_team'] = team_info(m.home_team)
            data['away_team'] = team_info(m.away_team)
            data['competition'] = m.competition.to_dict() if m.competition else None
            data['home_team_ranking'] = rankings_cache.get((m.competition_id, m.home_team_id))
            data['away_team_ranking'] = rankings_cache.get((m.competition_id, m.away_team_id))
            return data

        return jsonify({
            'message': 'Matches retrieved successfully',
            'team_id': team_id,
            'season': {
                'id': active_season.id,
                'name': active_season.name,
                'label': active_season.label,
            },
            'period': period,
            'total': len(matches),
            'competitions': competitions,
            'rankings': team_rankings,
            'matches': [_match_dict(m) for m in matches],
        }), 200

    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500

@match_sheet.route('/teams/<int:team_id>/matches/recent', methods=['GET'])
def get_team_recent_matches(team_id):
    """
    Les N derniers matchs terminés d'une équipe.
    Paramètre optionnel : limit (défaut 5)
    """
    try:
        limit = request.args.get('limit', 5, type=int)

        matches = Match.query.options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
        ).filter(
            Match.status == MatchStatus.COMPLETED.value,
            db.or_(
                Match.home_team_id == team_id,
                Match.away_team_id == team_id,
            ),
        ).order_by(Match.scheduled_date.desc())\
         .limit(limit)\
         .all()

        return jsonify({
            'message': f'Last {limit} completed matches retrieved successfully',
            'team_id': team_id,
            'total': len(matches),
            'matches': [match_full_dict(m) for m in matches],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/today', methods=['GET'])
def get_today_matches():
    """
    Matches du jour selon l'heure WAT (UTC+1).
    Paramètre optionnel : competition_id
    """
    try:
        competition_id = request.args.get('competition_id', type=int)

        now_wat   = datetime.now(WAT)
        start_utc = now_wat.replace(hour=0,  minute=0,  second=0,  microsecond=0)\
                           .astimezone(timezone.utc).replace(tzinfo=None)
        end_utc   = now_wat.replace(hour=23, minute=59, second=59, microsecond=999999)\
                           .astimezone(timezone.utc).replace(tzinfo=None)

        query = Match.query.options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
        ).filter(
            Match.scheduled_date >= start_utc,
            Match.scheduled_date <= end_utc,
        ).order_by(Match.scheduled_date.asc())

        if competition_id:
            query = query.filter(Match.competition_id == competition_id)

        matches = query.all()

        return jsonify({
            'message': "Today's matches retrieved successfully",
            'date_wat': now_wat.strftime('%Y-%m-%d'),
            'total': len(matches),
            'matches': [match_full_dict(m) for m in matches],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
# MATCH SHEET ROUTES
# ==========================================


@match_sheet.route('/matches/<int:match_id>/sheet', methods=['GET'])
def get_match_sheet(match_id):
    try:
        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        sheet = MatchSheet.query.filter_by(match_id=match_id).first()
        events = MatchEvent.query.filter_by(match_id=match_id).order_by(MatchEvent.minute).all()

        return jsonify({
            'match': match.to_dict(),
            'sheet': sheet.to_dict() if sheet else None,
            'events': [e.to_dict() for e in events],
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

        if existing_sheet and existing_sheet.is_validated:
            return jsonify({'error': 'Match sheet is already validated and cannot be modified'}), 409

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

        match.status = MatchStatus.IN_PROGRESS.value

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

        from olibo.ranking.utilities import recalculate_rankings
        match = Match.query.get(match_id)
        if match:
            recalculate_rankings(match.competition_id)

        return jsonify({'message': 'Match sheet validated successfully', 'sheet': sheet.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@match_sheet.route('/matches/<int:match_id>/close', methods=['POST'])
@jwt_required()
def close_match(match_id):
    try:
        user = get_authorized_user()

        if user.role not in ['referee', 'commissioner', 'super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        if match.status != MatchStatus.IN_PROGRESS.value:
            return jsonify({'error': 'Match is not in progress'}), 400

        match.status = MatchStatus.COMPLETED.value
        db.session.commit()

        from olibo.ranking.utilities import recalculate_rankings
        recalculate_rankings(match.competition_id)

        return jsonify({'message': 'Match closed', 'match': match.to_dict()}), 200

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

        if not all(k in data for k in ['member_id', 'event_type', 'minute']):
            return jsonify({'error': 'Missing required fields: member_id, event_type, minute'}), 400

        if data['event_type'] not in VALID_EVENT_TYPES:
            return jsonify({'error': f"Invalid event_type. Allowed: {list(VALID_EVENT_TYPES)}"}), 400

        minute = data['minute']
        if not isinstance(minute, int) or minute < 0 or minute > 130:
            return jsonify({'error': 'Minute must be an integer between 0 and 130'}), 400

        sheet = MatchSheet.query.filter_by(match_id=match_id).first()
        if sheet and sheet.is_validated:
            return jsonify({'error': 'Match sheet is already validated and cannot be modified'}), 409

        member = TeamMember.query.get(data['member_id'])

        if not member or member.team_id not in (match.home_team_id, match.away_team_id):
            return jsonify({'error': 'Member not part of this match'}), 404

        non_player_events = {'substitution'}
        if not member.is_player and data['event_type'] not in non_player_events:
            return jsonify({'error': f"Non-player members can only have event type: {non_player_events}"}), 400

        event = MatchEvent(
            match_id=match_id,
            member_id=data['member_id'],
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


@match_sheet.route('/matches/<int:match_id>/events/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_match_event(match_id, event_id):
    try:
        user = get_authorized_user()

        if user.role not in ['referee', 'commissioner', 'super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403

        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404

        sheet = MatchSheet.query.filter_by(match_id=match_id).first()
        if sheet and sheet.is_validated:
            return jsonify({'error': 'Match sheet is validated, events cannot be deleted'}), 409

        event = MatchEvent.query.filter_by(id=event_id, match_id=match_id).first()
        if not event:
            return jsonify({'error': 'Event not found'}), 404

        db.session.delete(event)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500