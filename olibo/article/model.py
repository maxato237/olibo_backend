from datetime import datetime
from olibo import db
from slugify import slugify


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