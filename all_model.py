from datetime import datetime
from olibo import db
from slugify import slugify
from olibo.common.enums import *


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50), nullable=False)  # Utilise UserRole.value
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    team_representative_of = db.relationship('Team', backref='representative', foreign_keys='Team.representative_id', uselist=False)
    tokens = db.relationship('Token', backref='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='voter', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', cascade='all, delete-orphan')
    incident_reports = db.relationship('IncidentReport', backref='reporter', cascade='all, delete-orphan')
    articles = db.relationship('Article', back_populates='author', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "role": self.role,
            "role_label": ROLE_LABELS_FR.get(self.role, self.role),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Token(db.Model):
    __tablename__ = 'tokens'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(500), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat()
        }


class Season(db.Model):
    __tablename__ = 'seasons'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    competitions = db.relationship('Competition', back_populates='season_obj', cascade='all, delete-orphan', lazy=True)
    licenses = db.relationship('License', back_populates='season', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


class Competition(db.Model):
    __tablename__ = 'competitions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    season = db.Column(db.String(100), nullable=False) 
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    competition_type = db.Column(db.Enum(CompetitionType, native_enum=False, validate_strings=True), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    season_obj = db.relationship('Season', back_populates='competitions')
    matches = db.relationship('Match', backref='competition', cascade='all, delete-orphan')
    rankings = db.relationship('Ranking', backref='competition', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "season": self.season,
            "season_id": self.season_id,
            "is_active": self.is_active,
            "competition_type": self.competition_type.value if self.competition_type is not None else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    logo = db.Column(db.String(500)) 
    description = db.Column(db.Text)
    representative_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    logo_public_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    members = db.relationship('TeamMember', backref='team', cascade='all, delete-orphan')
    registration = db.relationship('TeamRegistration', backref='team', uselist=False, cascade='all, delete-orphan')
    matches_home = db.relationship('Match', backref='home_team', foreign_keys='Match.home_team_id')
    matches_away = db.relationship('Match', backref='away_team', foreign_keys='Match.away_team_id')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "logo": self.logo,
            "description": self.description,
            "representative_id": self.representative_id,
            "logo_public_id": self.logo_public_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "member_count": len(self.members),
            "player_count": sum(1 for m in self.members if m.role == 'player'),
            "members": [member.to_dict() for member in self.members],
        }


class TeamMember(db.Model):
    __tablename__ = 'team_members'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    # Informations personnelles
    role = db.Column(db.String(50), nullable=False, default='player')
    # Valeurs possibles : player | coach | assistant_coach | fitness_coach |
    #                     doctor | physiotherapist | manager | other
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    photo = db.Column(db.String(500), nullable=True)  # URL or file path
    photo_public_id = db.Column(db.String(255), nullable=True)  # For Cloudinary management

    # Champs spécifiques aux joueurs (NULL si rôle != player)
    position = db.Column(db.String(50), nullable=True)
    jersey_number = db.Column(db.Integer, nullable=True)
    license_number = db.Column(db.String(100), unique=True, nullable=True)

    # Champs optionnels (tous membres)
    nationality = db.Column(db.String(3), nullable=True)
    nationality_label = db.Column(db.String(100), nullable=True)
    preferred_foot = db.Column(db.String(10), nullable=True)
    height_cm = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(1), nullable=True)
    category = db.Column(db.String(20), nullable=True)

    is_captain = db.Column(db.Boolean, default=False, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    licenses = db.relationship('License', back_populates='member', uselist=True, cascade='all, delete-orphan')
    match_events = db.relationship('MatchEvent', back_populates='member', cascade='all, delete-orphan')
    incident_reports = db.relationship('IncidentReport', back_populates='member')
    votes = db.relationship('Vote', back_populates='member', cascade='all, delete-orphan')
    vote_results = db.relationship('VoteResult', back_populates='member', cascade='all, delete-orphan')

    @property
    def is_player(self) -> bool:
        return self.role == 'player'

    def to_dict(self):
        data = {
            "id": self.id,
            "team_id": self.team_id,
            "role": self.role,
            "role_label": TEAM_MEMBER_ROLE_LABELS_FR.get(self.role, self.role),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "photo": self.photo,
            "photo_public_id": self.photo_public_id,
            "nationality": self.nationality,
            "nationality_label": self.nationality_label,
            "preferred_foot": self.preferred_foot,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "gender": self.gender,
            "category": self.category,
            "is_captain": self.is_captain,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.is_player:
            data.update({
                "position": self.position,
                "jersey_number": self.jersey_number,
                "license_number": self.license_number,
            })
        return data


class TeamRegistration(db.Model):
    __tablename__ = 'team_registrations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, unique=True)
    status = db.Column(db.String(50), default=RegistrationStatus.PENDING.value, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    validation_date = db.Column(db.DateTime)
    validated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejection_reason = db.Column(db.Text)
    documents_submitted = db.Column(db.JSON)

    # Relations
    validated_by = db.relationship('User', foreign_keys=[validated_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "status": self.status,
            "status_label": REGISTRATION_STATUS_LABELS_FR.get(self.status, self.status),
            "submission_date": self.submission_date.isoformat(),
            "validation_date": self.validation_date.isoformat() if self.validation_date else None,
            "rejection_reason": self.rejection_reason,
            "validated_by_id": self.validated_by_id,
        }


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


class License(db.Model):
    __tablename__ = 'licenses'

    __table_args__ = (
        db.UniqueConstraint('member_id', 'season_id', name='uq_licenses_member_season'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=True)
    license_number = db.Column(db.String(100), unique=True, nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    document_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    member = db.relationship('TeamMember', back_populates='licenses')
    season = db.relationship('Season', back_populates='licenses')

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "season_id": self.season_id,
            "license_number": self.license_number,
            "issue_date": self.issue_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "is_valid": self.is_valid,
            "is_active": self.is_active,
            "document_url": self.document_url,
            "created_at": self.created_at.isoformat(),
        }


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
            "updated_at": self.updated_at.isoformat()
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='XAF', nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)  # registration_fee, other
    status = db.Column(db.String(50), default=PaymentStatus.PENDING.value, nullable=False)
    transaction_id = db.Column(db.String(255), unique=True)
    payment_method = db.Column(db.String(50))  # card, mobile_money, bank_transfer, etc
    proof_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    team = db.relationship('Team')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "amount": self.amount,
            "currency": self.currency,
            "payment_type": self.payment_type,
            "payment_type_label": PAYMENT_TYPE_LABELS_FR.get(self.payment_type, self.payment_type),
            "status": self.status,
            "status_label": PAYMENT_STATUS_LABELS_FR.get(self.status, self.status),
            "transaction_id": self.transaction_id,
            "payment_method": self.payment_method,
            "proof_url": self.proof_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # match_scheduled, match_result, registration_validated, etc
    related_object_id = db.Column(db.Integer)  # ID de l'objet relié (match, team, etc)
    related_object_type = db.Column(db.String(50))  # Type de l'objet (match, team, etc)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "related_object_id": self.related_object_id,
            "related_object_type": self.related_object_type,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat()
        }


class IncidentReport(db.Model):
    __tablename__ = 'incident_reports'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=True)  # ← player_id → member_id (nullable : incident pas forcément lié à un membre)
    incident_type = db.Column(db.String(100), nullable=False)  # violent_conduct | unsporting_behavior | etc.
    description = db.Column(db.Text, nullable=False)
    minute = db.Column(db.Integer)
    severity = db.Column(db.String(50))   # low | medium | high
    status = db.Column(db.String(50), default='reported', nullable=False)  # reported | under_review | resolved
    resolution = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    match = db.relationship('Match')
    member = db.relationship('TeamMember', foreign_keys=[member_id], back_populates='incident_reports')

    def to_dict(self):
        return {
            "id": self.id,
            "match_id": self.match_id,
            "reporter_id": self.reporter_id,
            "member_id": self.member_id,
            "incident_type": self.incident_type,
            "description": self.description,
            "minute": self.minute,
            "severity": self.severity,
            "status": self.status,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


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


class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)

    excerpt = db.Column(db.Text)
    cover_image = db.Column(db.String(500))

    status = db.Column(db.String(20), default="draft", nullable=False)  
    # draft | published | archived

    content = db.Column(db.JSON, nullable=False)  
    # Stockage structuré par blocs

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)

    # Relations
    author = db.relationship('User', back_populates='articles')

    def generate_slug(self):
        self.slug = slugify(self.title)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "excerpt": self.excerpt,
            "cover_image": self.cover_image,
            "status": self.status,
            "content": self.content,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class News(db.Model):
    __tablename__ = 'news'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'))
    featured_image = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    author = db.relationship('User')
    competition = db.relationship('Competition')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author_id": self.author_id,
            "competition_id": self.competition_id,
            "featured_image": self.featured_image,
            "is_published": self.is_published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Media(db.Model):
    __tablename__ = 'medias'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    file_url = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # image, video
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'))
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    uploaded_by = db.relationship('User')
    competition = db.relationship('Competition')
    match = db.relationship('Match')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "uploaded_by_id": self.uploaded_by_id,
            "competition_id": self.competition_id,
            "match_id": self.match_id,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }