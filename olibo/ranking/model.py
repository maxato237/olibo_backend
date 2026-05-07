from datetime import datetime
from olibo import db

class Ranking(db.Model):
    __tablename__ = 'rankings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    position = db.Column(db.Integer, nullable=True)
    matches_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False)
    draws = db.Column(db.Integer, default=0, nullable=False)
    losses = db.Column(db.Integer, default=0, nullable=False)
    goals_for = db.Column(db.Integer, default=0, nullable=False)
    goals_against = db.Column(db.Integer, default=0, nullable=False)
    goal_difference = db.Column(db.Integer, default=0, nullable=False)
    points = db.Column(db.Integer, default=0, nullable=True)
    yellow_cards = db.Column(db.Integer, default=0, nullable=False)
    red_cards    = db.Column(db.Integer, default=0, nullable=False)
    clean_sheets = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    team = db.relationship('Team')

    def to_dict(self):
        return {
            "id": self.id,
            "competition_id": self.competition_id,
            "team_id": self.team_id,
            "position": self.position,
            "matches_played": self.matches_played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
            "clean_sheets": self.clean_sheets,
            "updated_at": self.updated_at.isoformat()
        }

