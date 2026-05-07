from datetime import datetime
from olibo import db


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