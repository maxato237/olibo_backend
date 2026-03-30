
import cloudinary
import cloudinary.uploader

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from olibo import config
import os
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=None):
    
    app = Flask(__name__)

    CORS(app,
         resources={r"/api/*": {"origins": [
             "file://",
             "http://localhost:4200",
         ]}},
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"]
    )

    cloudinary.config(
        cloud_name="dhupzvfe1",
        api_key="679196967497286",
        api_secret="aqkZ0jmkoM8Fgle15nZFMmZDpTY"
    )

    # Configuration de la base de données
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{config.Config.POSTGRESQL_CONNEXION['user']}:{config.Config.POSTGRESQL_CONNEXION['password']}"
        f"@{config.Config.POSTGRESQL_CONNEXION['host']}:{config.Config.POSTGRESQL_CONNEXION['port']}"
        f"/{config.Config.POSTGRESQL_CONNEXION['database']}"
    )

    # app.config['SQLALCHEMY_DATABASE_URI'] = config.Config.get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuration JWT
    app.config['SECRET_KEY'] = config.Config.SECRET_KEY
    app.config['JWT_SECRET_KEY'] = config.Config.SECRET_JWT_KEY
    app.config['JWT_TOKEN_LOCATION'] = config.Config.JWT_TOKEN_LOCATION
    app.config['JWT_HEADER_NAME'] = config.Config.JWT_HEADER_NAME
    app.config['JWT_HEADER_TYPE'] = config.Config.JWT_HEADER_TYPE
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_SESSION_COOKIE'] = False
 
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object(config.Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    with app.app_context():
        from olibo.announcements.routes import announcements
        from olibo.competition.routes import competition
        from olibo.incident_report.routes import incident_report
        from olibo.match_sheet.routes import match_sheet
        from olibo.media.routes import media
        from olibo.notification.routes import notification
        from olibo.payment.routes import payment
        from olibo.ranking.routes import ranking
        from olibo.team.routes import team
        from olibo.users.routes import users
        from olibo.voting.routes import voting
        from olibo.auth.routes import auth
        from olibo.license.routes import license
        from olibo.common.routes import enum
        from olibo.article.routes import article

        app.register_blueprint(announcements, url_prefix='/api/announcements')
        app.register_blueprint(competition, url_prefix='/api/competition')
        app.register_blueprint(incident_report, url_prefix='/api/incident_report')
        app.register_blueprint(match_sheet, url_prefix='/api/match_sheet')
        app.register_blueprint(media, url_prefix='/api/media')
        app.register_blueprint(notification, url_prefix='/api/notification')
        app.register_blueprint(payment, url_prefix='/api/payment')
        app.register_blueprint(ranking, url_prefix='/api/ranking')
        app.register_blueprint(team, url_prefix='/api/team')
        app.register_blueprint(users, url_prefix='/api/users')
        app.register_blueprint(voting, url_prefix='/api/voting')
        app.register_blueprint(auth, url_prefix='/api/auth')
        app.register_blueprint(license, url_prefix='/api/license')
        app.register_blueprint(enum, url_prefix='/api/enum')
        app.register_blueprint(article, url_prefix='/api/article')
        
        db.create_all()
    
    return app