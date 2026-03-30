from datetime import datetime
from olibo import db

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
