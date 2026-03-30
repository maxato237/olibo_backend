from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

db = SQLAlchemy()

# ============= ENUMS =============
class UserRole(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN_COMPETITION = "admin_competition"
    OPERATOR = "operator"
    REFEREE = "referee"
    COMMISSIONER = "commissioner"
    TEAM_CAPTAIN = "team_captain"
    COACH = "coach"
    PLAYER = "player"
    SPECTATOR = "spectator"
    JOURNALIST = "journalist"

class RegistrationStatus(Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"

class MatchStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CardType(Enum):
    YELLOW = "yellow"
    RED = "red"

class VoteType(Enum):
    PLAYER_OF_DAY = "player_of_day"
    PLAYER_OF_COMPETITION = "player_of_competition"

class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

# ============= USERS / AUTH =============
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
    team_captain_of = db.relationship('Team', backref='captain', foreign_keys='Team.captain_id', uselist=False)
    team_coach_of = db.relationship('Team', backref='coach', foreign_keys='Team.coach_id', uselist=False)
    player = db.relationship('Player', backref='user', uselist=False, foreign_keys='Player.user_id')
    tokens = db.relationship('Token', backref='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='voter', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', cascade='all, delete-orphan')
    incident_reports = db.relationship('IncidentReport', backref='reporter', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
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


# ============= TEAM =============
class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    logo = db.Column(db.String(500))  # URL or file path
    description = db.Column(db.Text)
    captain_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    coach_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_registered = db.Column(db.Boolean, default=False, nullable=False)
    registration_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    players = db.relationship('Player', backref='team', cascade='all, delete-orphan')
    registration = db.relationship('TeamRegistration', backref='team', uselist=False, cascade='all, delete-orphan')
    matches_home = db.relationship('Match', backref='home_team', foreign_keys='Match.home_team_id')
    matches_away = db.relationship('Match', backref='away_team', foreign_keys='Match.away_team_id')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "logo": self.logo,
            "description": self.description,
            "captain_id": self.captain_id,
            "coach_id": self.coach_id,
            "is_registered": self.is_registered,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "player_count": len(self.players)
        }


class Player(db.Model):
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    license_number = db.Column(db.String(100), unique=True, nullable=False)
    position = db.Column(db.String(50), nullable=False)  # goalkeeper, defender, midfielder, forward
    jersey_number = db.Column(db.Integer, nullable=False)
    photo = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    license = db.relationship('License', backref='player', uselist=False, cascade='all, delete-orphan')
    match_events = db.relationship('MatchEvent', backref='player', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "license_number": self.license_number,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "photo": self.photo,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============= REGISTRATION =============
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
            "submission_date": self.submission_date.isoformat(),
            "validation_date": self.validation_date.isoformat() if self.validation_date else None,
            "rejection_reason": self.rejection_reason,
            "validated_by_id": self.validated_by_id
        }


# ============= LICENSE =============
class License(db.Model):
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, unique=True)
    license_number = db.Column(db.String(100), unique=True, nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)
    document_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "license_number": self.license_number,
            "issue_date": self.issue_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "is_valid": self.is_valid,
            "document_url": self.document_url,
            "created_at": self.created_at.isoformat()
        }


# ============= COMPETITION =============
class Competition(db.Model):
    __tablename__ = 'competitions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    season = db.Column(db.Integer, nullable=False)  # Numéro de saison
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
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
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============= MATCH & MATCH SHEET =============
class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
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
    referee = db.relationship('User', foreign_keys=[referee_id])
    match_sheet = db.relationship('MatchSheet', backref='match', uselist=False, cascade='all, delete-orphan')
    match_events = db.relationship('MatchEvent', backref='match', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "competition_id": self.competition_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "scheduled_date": self.scheduled_date.isoformat(),
            "status": self.status,
            "home_team_goals": self.home_team_goals,
            "away_team_goals": self.away_team_goals,
            "matchday": self.matchday,
            "location": self.location,
            "referee_id": self.referee_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
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
            "pdf_url": self.pdf_url
        }


class MatchEvent(db.Model):
    __tablename__ = 'match_events'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # goal, assist, yellow_card, red_card, substitution
    minute = db.Column(db.Integer, nullable=False)
    card_type = db.Column(db.String(20))  # yellow or red
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "match_id": self.match_id,
            "player_id": self.player_id,
            "event_type": self.event_type,
            "minute": self.minute,
            "card_type": self.card_type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat()
        }


# ============= RANKING =============
class Ranking(db.Model):
    __tablename__ = 'rankings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    matches_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False)
    draws = db.Column(db.Integer, default=0, nullable=False)
    losses = db.Column(db.Integer, default=0, nullable=False)
    goals_for = db.Column(db.Integer, default=0, nullable=False)
    goals_against = db.Column(db.Integer, default=0, nullable=False)
    goal_difference = db.Column(db.Integer, default=0, nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)
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


# ============= VOTING =============
class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    vote_type = db.Column(db.String(50), nullable=False)  # player_of_day, player_of_competition
    matchday = db.Column(db.Integer)  # Pour player_of_day
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    player = db.relationship('Player')
    competition = db.relationship('Competition')
    
    __table_args__ = (
        db.UniqueConstraint('voter_id', 'vote_type', 'matchday', 'competition_id', name='unique_vote_per_matchday'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "voter_id": self.voter_id,
            "player_id": self.player_id,
            "competition_id": self.competition_id,
            "vote_type": self.vote_type,
            "matchday": self.matchday,
            "created_at": self.created_at.isoformat()
        }


class VoteResult(db.Model):
    __tablename__ = 'vote_results'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    vote_type = db.Column(db.String(50), nullable=False)
    matchday = db.Column(db.Integer)
    vote_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    player = db.relationship('Player')
    competition = db.relationship('Competition')

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "competition_id": self.competition_id,
            "vote_type": self.vote_type,
            "matchday": self.matchday,
            "vote_count": self.vote_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============= NOTIFICATION =============
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


# ============= PAYMENT =============
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
            "status": self.status,
            "transaction_id": self.transaction_id,
            "payment_method": self.payment_method,
            "proof_url": self.proof_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============= INCIDENT REPORT =============
class IncidentReport(db.Model):
    __tablename__ = 'incident_reports'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    incident_type = db.Column(db.String(100), nullable=False)  # violent_conduct, unsporting_behavior, etc
    description = db.Column(db.Text, nullable=False)
    minute = db.Column(db.Integer)
    severity = db.Column(db.String(50))  # low, medium, high
    status = db.Column(db.String(50), default='reported', nullable=False)  # reported, under_review, resolved
    resolution = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    match = db.relationship('Match')
    player = db.relationship('Player')

    def to_dict(self):
        return {
            "id": self.id,
            "match_id": self.match_id,
            "reporter_id": self.reporter_id,
            "player_id": self.player_id,
            "incident_type": self.incident_type,
            "description": self.description,
            "minute": self.minute,
            "severity": self.severity,
            "status": self.status,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============= MEDIA =============
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


# ============= NEWS / ANNOUNCEMENTS =============
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
