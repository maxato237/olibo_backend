from datetime import date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from olibo import db
from olibo.common.helpers import get_authorized_user
from olibo.license.routes import revoke_season_licenses
from olibo.season.model import Season

seasons = Blueprint('seasons', __name__)


@seasons.route('', methods=['GET'])
def get_all_seasons():
    try:
        all_seasons = Season.query.order_by(Season.start_date.desc()).all()
        return jsonify({
            'message': 'Seasons retrieved successfully',
            'total': len(all_seasons),
            'seasons': [s.to_dict() for s in all_seasons],
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seasons.route('/active', methods=['GET'])
def get_active_season():
    try:
        season = Season.query.filter_by(is_active=True).first()
        if not season:
            return jsonify({'message': 'No active season', 'season': None}), 200
        return jsonify({'season': season.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seasons.route('/<int:season_id>', methods=['GET'])
def get_season(season_id):
    try:
        season = Season.query.get(season_id)
        if not season:
            return jsonify({'error': 'Season not found'}), 404
        return jsonify({
            'message': 'Season retrieved successfully',
            'season': season.to_dict(),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seasons.route('', methods=['POST'])
@jwt_required()
def create_season():
    try:
        user = get_authorized_user()
        if user.role != 'super_admin':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not all(k in data for k in ['name', 'label', 'start_date', 'end_date']):
            return jsonify({'error': 'Missing required fields: name, label, start_date, end_date'}), 400

        start = date.fromisoformat(data['start_date'])
        end = date.fromisoformat(data['end_date'])
        if end <= start:
            return jsonify({'error': 'end_date must be after start_date'}), 400

        if data.get('is_active', False):
            Season.query.update({'is_active': False})

        season = Season(
            name=data['name'],
            label=data['label'],
            start_date=start,
            end_date=end,
            is_active=data.get('is_active', False),
        )
        db.session.add(season)
        db.session.commit()

        return jsonify({
            'message': 'Season created successfully',
            'season': season.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@seasons.route('/<int:season_id>', methods=['PUT'])
@jwt_required()
def update_season(season_id):
    try:
        user = get_authorized_user()
        if user.role != 'super_admin':
            return jsonify({'error': 'Unauthorized'}), 403

        season = Season.query.get(season_id)
        if not season:
            return jsonify({'error': 'Season not found'}), 404

        data = request.get_json()

        if 'name' in data:
            season.name = data['name']
        if 'label' in data:
            season.label = data['label']
        if 'start_date' in data:
            season.start_date = date.fromisoformat(data['start_date'])
        if 'end_date' in data:
            season.end_date = date.fromisoformat(data['end_date'])
        if 'is_active' in data:
            if data['is_active']:
                Season.query.filter(Season.id != season_id).update({'is_active': False})
            elif season.is_active and not data['is_active']:
                revoke_season_licenses(season_id)
            season.is_active = data['is_active']

        db.session.commit()

        return jsonify({
            'message': 'Season updated successfully',
            'season': season.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@seasons.route('/<int:season_id>/teams/stats', methods=['GET'])
def get_season_team_stats(season_id):
    from olibo.competition.model import Competition
    from olibo.license.model import License
    from olibo.match_sheet.model import Match, MatchEvent
    from olibo.ranking.model import Ranking
    from olibo.team.model import Team, TeamMember

    try:
        season = Season.query.get(season_id)
        if not season:
            return jsonify({'error': 'Season not found'}), 404

        if not Competition.query.filter_by(season_id=season_id).first():
            return jsonify({'season': season.to_dict(), 'total': 0, 'teams': []}), 200

        # ── 1. Classement agrégé par équipe sur toutes les compétitions de la saison ──
        ranking_rows = (
            db.session.query(
                Ranking.team_id,
                func.sum(Ranking.matches_played).label('matches_played'),
                func.sum(Ranking.wins).label('wins'),
                func.sum(Ranking.draws).label('draws'),
                func.sum(Ranking.losses).label('losses'),
                func.sum(Ranking.goals_for).label('goals_for'),
                func.sum(Ranking.goals_against).label('goals_against'),
                func.sum(Ranking.goal_difference).label('goal_difference'),
                func.sum(Ranking.points).label('points'),
                func.min(Ranking.position).label('best_position'),
            )
            .join(Competition, Competition.id == Ranking.competition_id)
            .filter(Competition.season_id == season_id)
            .group_by(Ranking.team_id)
            .all()
        )

        # ── 2. Cartons jaunes par équipe ──
        yellow_rows = (
            db.session.query(TeamMember.team_id, func.count(MatchEvent.id).label('n'))
            .join(MatchEvent, MatchEvent.member_id == TeamMember.id)
            .join(Match, Match.id == MatchEvent.match_id)
            .join(Competition, Competition.id == Match.competition_id)
            .filter(Competition.season_id == season_id, MatchEvent.event_type == 'yellow_card')
            .group_by(TeamMember.team_id)
            .all()
        )

        # ── 3. Cartons rouges par équipe ──
        red_rows = (
            db.session.query(TeamMember.team_id, func.count(MatchEvent.id).label('n'))
            .join(MatchEvent, MatchEvent.member_id == TeamMember.id)
            .join(Match, Match.id == MatchEvent.match_id)
            .join(Competition, Competition.id == Match.competition_id)
            .filter(Competition.season_id == season_id, MatchEvent.event_type == 'red_card')
            .group_by(TeamMember.team_id)
            .all()
        )

        # ── 4. Clean sheets : matchs terminés où l'adversaire n'a pas marqué ──
        home_cs = (
            db.session.query(Match.home_team_id.label('team_id'), func.count(Match.id).label('n'))
            .join(Competition, Competition.id == Match.competition_id)
            .filter(
                Competition.season_id == season_id,
                Match.status == 'completed',
                Match.away_team_goals == 0,
            )
            .group_by(Match.home_team_id)
            .all()
        )
        away_cs = (
            db.session.query(Match.away_team_id.label('team_id'), func.count(Match.id).label('n'))
            .join(Competition, Competition.id == Match.competition_id)
            .filter(
                Competition.season_id == season_id,
                Match.status == 'completed',
                Match.home_team_goals == 0,
            )
            .group_by(Match.away_team_id)
            .all()
        )

        # ── 5. Joueurs licenciés actifs pour la saison ──
        licensed_rows = (
            db.session.query(TeamMember.team_id, func.count(License.id).label('n'))
            .join(License, License.member_id == TeamMember.id)
            .filter(License.season_id == season_id, License.is_active == True)
            .group_by(TeamMember.team_id)
            .all()
        )

        # ── 6. Effectif actif total par équipe ──
        squad_rows = (
            db.session.query(TeamMember.team_id, func.count(TeamMember.id).label('n'))
            .filter(TeamMember.is_active == True)
            .group_by(TeamMember.team_id)
            .all()
        )

        # ── Index des maps ──
        yellow_map   = {r.team_id: r.n for r in yellow_rows}
        red_map      = {r.team_id: r.n for r in red_rows}
        licensed_map = {r.team_id: r.n for r in licensed_rows}
        squad_map    = {r.team_id: r.n for r in squad_rows}

        cs_map = {}
        for r in home_cs:
            cs_map[r.team_id] = cs_map.get(r.team_id, 0) + r.n
        for r in away_cs:
            cs_map[r.team_id] = cs_map.get(r.team_id, 0) + r.n

        # ── Pré-chargement des équipes ──
        team_ids = [r.team_id for r in ranking_rows]
        teams_by_id = {t.id: t for t in Team.query.filter(Team.id.in_(team_ids)).all()}

        # ── Construction de la réponse ──
        results = []
        for row in ranking_rows:
            team = teams_by_id.get(row.team_id)
            if not team:
                continue
            results.append({
                'team_id':   row.team_id,
                'team_name': team.name,
                'team_logo': team.logo,
                'ranking': {
                    'best_position':   row.best_position,
                    'matches_played':  row.matches_played  or 0,
                    'wins':            row.wins            or 0,
                    'draws':           row.draws           or 0,
                    'losses':          row.losses          or 0,
                    'goals_for':       row.goals_for       or 0,
                    'goals_against':   row.goals_against   or 0,
                    'goal_difference': row.goal_difference or 0,
                    'points':          row.points          or 0,
                },
                'discipline': {
                    'yellow_cards': yellow_map.get(row.team_id, 0),
                    'red_cards':    red_map.get(row.team_id, 0),
                },
                'clean_sheets':    cs_map.get(row.team_id, 0),
                'squad': {
                    'total_members':    squad_map.get(row.team_id, 0),
                    'licensed_players': licensed_map.get(row.team_id, 0),
                },
            })

        results.sort(key=lambda x: (x['ranking']['points'], x['ranking']['goal_difference']), reverse=True)

        return jsonify({
            'season': season.to_dict(),
            'total':  len(results),
            'teams':  results,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@seasons.route('/<int:season_id>', methods=['DELETE'])
@jwt_required()
def delete_season(season_id):
    try:
        user = get_authorized_user()
        if user.role != 'super_admin':
            return jsonify({'error': 'Unauthorized'}), 403

        season = Season.query.get(season_id)
        if not season:
            return jsonify({'error': 'Season not found'}), 404

        revoke_season_licenses(season_id)
        db.session.delete(season)
        db.session.commit()
        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
