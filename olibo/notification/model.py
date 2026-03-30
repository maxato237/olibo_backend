from datetime import datetime
from olibo import db

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

