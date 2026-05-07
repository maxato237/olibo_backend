from datetime import datetime
from olibo import db
from olibo.common.enums import MatchStatus, MATCH_STATUS_LABELS_FR, CARD_TYPE_LABELS_FR, MATCH_EVENT_TYPE_LABELS_FR


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default=MatchStatus.SCHEDULED.value, nullable=False)
    home_team_goals = db.Column(db.Integer, default=0)
    away_team_goals = db.Column(db.Integer, default=0)
    matchday = db.Column(db.Integer)
    location = db.Column(db.String(255))
    referee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    season = db.relationship('Season', foreign_keys=[season_id])
    referee = db.relationship('User', foreign_keys=[referee_id])
    match_sheet = db.relationship('MatchSheet', backref='match', uselist=False, cascade='all, delete-orphan')
    match_events = db.relationship('MatchEvent', backref='match', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "competition_id": self.competition_id,
            "season_id": self.season_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "scheduled_date": self.scheduled_date.isoformat(),
            "status": self.status,
            "status_label": MATCH_STATUS_LABELS_FR.get(self.status, self.status),
            "home_team_goals": self.home_team_goals,
            "away_team_goals": self.away_team_goals,
            "matchday": self.matchday,
            "location": self.location,
            "referee_id": self.referee_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class MatchSheet(db.Model):
    __tablename__ = 'match_sheets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False, unique=True)
    filled_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    validated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_validated = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text)
    filled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    validated_at = db.Column(db.DateTime)
    pdf_url = db.Column(db.String(500))

    # Relations
    filled_by = db.relationship('User', foreign_keys=[filled_by_id])
    validated_by = db.relationship('User', foreign_keys=[validated_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "match_id": self.match_id,
            "filled_by_id": self.filled_by_id,
            "validated_by_id": self.validated_by_id,
            "is_validated": self.is_validated,
            "notes": self.notes,
            "filled_at": self.filled_at.isoformat(),
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "pdf_url": self.pdf_url,
        }


class MatchEvent(db.Model):
    __tablename__ = 'match_events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)

    # ── Référence vers team_members (anciennement players) ────────────────────
    member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False)

    event_type = db.Column(db.String(50), nullable=False)
    # Valeurs possibles : goal | assist | yellow_card | red_card | substitution
    minute = db.Column(db.Integer, nullable=False)
    card_type = db.Column(db.String(20))  # yellow | red (renseigné si event_type == *_card)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    member = db.relationship('TeamMember', back_populates='match_events')

    def to_dict(self):
        return {
            "id": self.id,
            "match_id": self.match_id,
            "member_id": self.member_id,
            "event_type": self.event_type,
            "event_type_label": MATCH_EVENT_TYPE_LABELS_FR.get(self.event_type, self.event_type),
            "minute": self.minute,
            "card_type": self.card_type,
            "card_type_label": CARD_TYPE_LABELS_FR.get(self.card_type, self.card_type) if self.card_type else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }