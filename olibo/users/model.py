from datetime import datetime
from olibo import db
from olibo.common.enums import ROLE_LABELS_FR


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