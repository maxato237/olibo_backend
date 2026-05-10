from datetime import datetime
from olibo import db


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
        def _name(user):
            if not user:
                return None
            return f"{user.first_name or ''} {user.last_name or ''}".strip() or f"#{user.id}"

        return {
            "id": self.id,
            "match_id": self.match_id,
            "reporter_id": self.reporter_id,
            "reporter_name": _name(self.reporter),
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