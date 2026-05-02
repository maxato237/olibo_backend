from olibo import db
from olibo.ranking.model import Ranking
from olibo.match_sheet.model import Match
from olibo.common.enums import MatchStatus


def recalculate_rankings(competition_id):
    completed_matches = Match.query.filter_by(
        competition_id=competition_id,
        status=MatchStatus.COMPLETED.value
    ).all()

    stats = {}

    def init_team(team_id):
        if team_id not in stats:
            stats[team_id] = {
                'matches_played': 0, 'wins': 0, 'draws': 0,
                'losses': 0, 'goals_for': 0, 'goals_against': 0
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

    for team_id, s in stats.items():
        s['points'] = s['wins'] * 3 + s['draws']
        s['goal_difference'] = s['goals_for'] - s['goals_against']

    sorted_teams = sorted(
        stats.items(),
        key=lambda x: (x[1]['points'], x[1]['goal_difference'], x[1]['goals_for']),
        reverse=True
    )

    for position, (team_id, s) in enumerate(sorted_teams, start=1):
        ranking = Ranking.query.filter_by(
            competition_id=competition_id,
            team_id=team_id
        ).first()

        if ranking:
            ranking.position = position
            ranking.matches_played = s['matches_played']
            ranking.wins = s['wins']
            ranking.draws = s['draws']
            ranking.losses = s['losses']
            ranking.goals_for = s['goals_for']
            ranking.goals_against = s['goals_against']
            ranking.goal_difference = s['goal_difference']
            ranking.points = s['points']
        else:
            ranking = Ranking(
                competition_id=competition_id,
                team_id=team_id,
                position=position,
                **s
            )
            db.session.add(ranking)

    db.session.commit()
