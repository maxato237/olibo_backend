from datetime import datetime
from olibo import db

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