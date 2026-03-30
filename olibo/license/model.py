from datetime import datetime
from olibo import db


class License(db.Model):
    __tablename__ = 'licenses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('team_members.id'), nullable=False, unique=True)  # ← player_id → member_id
    license_number = db.Column(db.String(100), unique=True, nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)
    document_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relation
    member = db.relationship('TeamMember', back_populates='license')

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "license_number": self.license_number,
            "issue_date": self.issue_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "is_valid": self.is_valid,
            "document_url": self.document_url,
            "created_at": self.created_at.isoformat(),
        }