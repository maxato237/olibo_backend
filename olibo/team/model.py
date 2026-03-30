from datetime import datetime
from olibo import db
from olibo.common.enums import RegistrationStatus


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    logo = db.Column(db.String(500)) 
    description = db.Column(db.Text)
    representative_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    captain_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    coach_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_registered = db.Column(db.Boolean, default=False, nullable=False)
    registration_date = db.Column(db.DateTime)
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
            "captain_id": self.captain_id,
            "logo_public_id": self.logo_public_id,
            "coach_id": self.coach_id,
            "is_registered": self.is_registered,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "member_count": len(self.members),
            "player_count": sum(1 for m in self.members if m.role == 'player'),
            "members": [member.to_dict() for member in self.members],
        }


class TeamMember(db.Model):
    """
    Représente tout membre d'une équipe, qu'il soit joueur, entraîneur,
    médecin, kinésithérapeute, etc.
    Les champs liés au jeu (position, jersey_number, license_number) ne sont
    renseignés que lorsque role == 'player'.
    """
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

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    license = db.relationship('License', backref='team_member', uselist=False, cascade='all, delete-orphan')
    match_events = db.relationship('MatchEvent', backref='team_member', cascade='all, delete-orphan')

    @property
    def is_player(self) -> bool:
        return self.role == 'player'

    def to_dict(self):
        data = {
            "id": self.id,
            "team_id": self.team_id,
            "role": self.role,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "photo": self.photo,
            "photo_public_id": self.photo_public_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        # Inclure les champs joueur uniquement si pertinent
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
            "submission_date": self.submission_date.isoformat(),
            "validation_date": self.validation_date.isoformat() if self.validation_date else None,
            "rejection_reason": self.rejection_reason,
            "validated_by_id": self.validated_by_id,
        }