from datetime import datetime
from olibo import db
from olibo.common.enums import VOTE_TYPE_LABELS_FR


class Vote(db.Model):
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False)  # ← player_id → member_id
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    vote_type = db.Column(db.String(50), nullable=False)  # player_of_day | player_of_competition
    matchday = db.Column(db.Integer)  # Renseigné si vote_type == player_of_day
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    member = db.relationship('TeamMember', foreign_keys=[member_id], back_populates='votes')
    competition = db.relationship('Competition')

    __table_args__ = (
        db.UniqueConstraint(
            'voter_id', 'vote_type', 'matchday', 'competition_id',
            name='unique_vote_per_matchday'
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "voter_id": self.voter_id,
            "member_id": self.member_id,
            "competition_id": self.competition_id,
            "vote_type": self.vote_type,
            "vote_type_label": VOTE_TYPE_LABELS_FR.get(self.vote_type, self.vote_type),
            "matchday": self.matchday,
            "created_at": self.created_at.isoformat(),
        }


class VoteResult(db.Model):
    __tablename__ = 'vote_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False)  # ← player_id → member_id
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    vote_type = db.Column(db.String(50), nullable=False)  # player_of_day | player_of_competition
    matchday = db.Column(db.Integer)
    vote_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    member = db.relationship('TeamMember', foreign_keys=[member_id], back_populates='vote_results')
    competition = db.relationship('Competition')

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "competition_id": self.competition_id,
            "vote_type": self.vote_type,
            "vote_type_label": VOTE_TYPE_LABELS_FR.get(self.vote_type, self.vote_type),
            "matchday": self.matchday,
            "vote_count": self.vote_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }