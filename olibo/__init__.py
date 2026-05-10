
import cloudinary
import cloudinary.uploader
import os
import yaml

from datetime import timedelta
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flasgger import Swagger
from olibo import config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",          # dev — remplacer par "redis://..." en production
    default_limits=[]
)

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
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET')
    )

    # Configuration de la base de données
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{config.Config.POSTGRESQL_CONNEXION['user']}:{config.Config.POSTGRESQL_CONNEXION['password']}"
        f"@{config.Config.POSTGRESQL_CONNEXION['host']}:{config.Config.POSTGRESQL_CONNEXION['port']}"
        f"/{config.Config.POSTGRESQL_CONNEXION['database']}?sslmode=disable"
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuration JWT
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object(config.Config)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY'))  # NOSONAR
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config.get('JWT_SECRET_KEY'))  # NOSONAR
    app.config['JWT_TOKEN_LOCATION'] = app.config.get('JWT_TOKEN_LOCATION', config.Config.JWT_TOKEN_LOCATION)
    app.config['JWT_HEADER_NAME'] = app.config.get('JWT_HEADER_NAME', config.Config.JWT_HEADER_NAME)
    app.config['JWT_HEADER_TYPE'] = app.config.get('JWT_HEADER_TYPE', config.Config.JWT_HEADER_TYPE)
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_SESSION_COOKIE'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        from olibo.announcements.routes import announcements
        from olibo.competition.routes import competition
        from olibo.incident_report.routes import incident_report
        from olibo.match_sheet.routes import match_sheet
        from olibo.media.routes import media
        from olibo.notification.routes import notification
        from olibo.payment.routes import payment
        from olibo.ranking.routes import ranking
        from olibo.season.routes import seasons
        from olibo.team.routes import team
        from olibo.users.routes import users
        from olibo.voting.routes import voting
        from olibo.auth.routes import auth
        from olibo.license.routes import license
        from olibo.license.render_routes import license_render
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
        app.register_blueprint(seasons, url_prefix='/api/seasons')
        app.register_blueprint(team, url_prefix='/api/team')
        app.register_blueprint(users, url_prefix='/api/users')
        app.register_blueprint(voting, url_prefix='/api/voting')
        app.register_blueprint(auth, url_prefix='/api/auth')
        app.register_blueprint(license, url_prefix='/api/license')
        app.register_blueprint(license_render)
        app.register_blueprint(enum, url_prefix='/api/enum')
        app.register_blueprint(article, url_prefix='/api/article')

        swagger_path = os.path.join(os.path.dirname(app.root_path), 'swagger.yaml')
        with open(swagger_path, 'r', encoding='utf-8') as f:
            swagger_template = yaml.safe_load(f)
        Swagger(app, template=swagger_template)

        db.create_all()

    return app
