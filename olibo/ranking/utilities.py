from sqlalchemy import func
from olibo import db
from olibo.ranking.model import Ranking
from olibo.match_sheet.model import Match, MatchEvent
from olibo.team.model import TeamMember
from olibo.common.enums import MatchStatus, RANKING_PRESET_RULES


def recalculate_rankings(competition_id):
    from olibo.competition.model import Competition

    competition = Competition.query.get(competition_id)
    if not competition:
        return

    rules = competition.ranking_rules or {}
    tiebreaker_order = (
        rules.get("tiebreaker_order")
        or RANKING_PRESET_RULES.get(rules.get("preset", "ligue_1"), [])
    )

    completed_matches = Match.query.filter_by(
        competition_id=competition_id,
        status=MatchStatus.COMPLETED.value
    ).all()

    stats = {}

    def init_team(team_id):
        if team_id not in stats:
            stats[team_id] = {
                'matches_played': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                'goals_for': 0, 'goals_against': 0, 'goal_difference': 0,
                'points': 0, 'clean_sheets': 0,
                'yellow_cards': 0, 'red_cards': 0,
            }

    for match in completed_matches:
        h, a = match.home_team_id, match.away_team_id
        hg, ag = match.home_team_goals, match.away_team_goals

        init_team(h)
        init_team(a)

        stats[h]['matches_played'] += 1
        stats[a]['matches_played'] += 1
        stats[h]['goals_for'] += hg
        stats[h]['goals_against'] += ag
        stats[a]['goals_for'] += ag
        stats[a]['goals_against'] += hg

        if hg > ag:
            stats[h]['wins'] += 1
            stats[a]['losses'] += 1
        elif hg == ag:
            stats[h]['draws'] += 1
            stats[a]['draws'] += 1
        else:
            stats[a]['wins'] += 1
            stats[h]['losses'] += 1

        if ag == 0:
            stats[h]['clean_sheets'] += 1
        if hg == 0:
            stats[a]['clean_sheets'] += 1

    for team_id, s in stats.items():
        s['points'] = s['wins'] * 3 + s['draws']
        s['goal_difference'] = s['goals_for'] - s['goals_against']

    # Cartons agrégés depuis MatchEvent uniquement
    for team_id in stats:
        stats[team_id]['yellow_cards'] = (
            db.session.query(func.count(MatchEvent.id))
            .join(Match, MatchEvent.match_id == Match.id)
            .join(TeamMember, MatchEvent.member_id == TeamMember.id)
            .filter(
                Match.competition_id == competition_id,
                TeamMember.team_id == team_id,
                MatchEvent.event_type == 'yellow_card',
            ).scalar() or 0
        )
        stats[team_id]['red_cards'] = (
            db.session.query(func.count(MatchEvent.id))
            .join(Match, MatchEvent.match_id == Match.id)
            .join(TeamMember, MatchEvent.member_id == TeamMember.id)
            .filter(
                Match.competition_id == competition_id,
                TeamMember.team_id == team_id,
                MatchEvent.event_type == 'red_card',
            ).scalar() or 0
        )

    # Confrontations directes (H2H) : points et diff de buts entre chaque paire
    h2h = {}
    for match in completed_matches:
        h, a = match.home_team_id, match.away_team_id
        hg, ag = match.home_team_goals, match.away_team_goals

        for key in [(h, a), (a, h)]:
            if key not in h2h:
                h2h[key] = {'points': 0, 'gd': 0}

        h2h[(h, a)]['gd'] += hg - ag
        h2h[(a, h)]['gd'] += ag - hg

        if hg > ag:
            h2h[(h, a)]['points'] += 3
        elif hg == ag:
            h2h[(h, a)]['points'] += 1
            h2h[(a, h)]['points'] += 1
        else:
            h2h[(a, h)]['points'] += 3

    all_teams = list(stats.keys())

    def make_sort_key(team_id):
        s = stats[team_id]
        key = []
        for tb in tiebreaker_order:
            if tb == 'points':
                key.append(-s['points'])
            elif tb == 'goal_difference':
                key.append(-s['goal_difference'])
            elif tb == 'goals_for':
                key.append(-s['goals_for'])
            elif tb == 'clean_sheets':
                key.append(-s['clean_sheets'])
            elif tb == 'fair_play':
                key.append(s['yellow_cards'] + s['red_cards'] * 3)
            elif tb == 'head_to_head':
                h2h_pts = sum(
                    h2h.get((team_id, other), {}).get('points', 0)
                    for other in all_teams if other != team_id
                )
                h2h_gd = sum(
                    h2h.get((team_id, other), {}).get('gd', 0)
                    for other in all_teams if other != team_id
                )
                key.extend([-h2h_pts, -h2h_gd])
        return key

    sorted_teams = sorted(all_teams, key=make_sort_key)

    for position, team_id in enumerate(sorted_teams, start=1):
        s = stats[team_id]
        ranking = Ranking.query.filter_by(
            competition_id=competition_id,
            team_id=team_id,
        ).first()

        if ranking:
            ranking.position       = position
            ranking.matches_played = s['matches_played']
            ranking.wins           = s['wins']
            ranking.draws          = s['draws']
            ranking.losses         = s['losses']
            ranking.goals_for      = s['goals_for']
            ranking.goals_against  = s['goals_against']
            ranking.goal_difference = s['goal_difference']
            ranking.points         = s['points']
            ranking.clean_sheets   = s['clean_sheets']
            ranking.yellow_cards   = s['yellow_cards']
            ranking.red_cards      = s['red_cards']
        else:
            ranking = Ranking(
                competition_id=competition_id,
                team_id=team_id,
                position=position,
                matches_played=s['matches_played'],
                wins=s['wins'],
                draws=s['draws'],
                losses=s['losses'],
                goals_for=s['goals_for'],
                goals_against=s['goals_against'],
                goal_difference=s['goal_difference'],
                points=s['points'],
                clean_sheets=s['clean_sheets'],
                yellow_cards=s['yellow_cards'],
                red_cards=s['red_cards'],
            )
            db.session.add(ranking)

    db.session.commit()
