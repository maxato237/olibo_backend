import cloudinary
import cloudinary.uploader
import os
import yaml

from datetime import timedelta
from urllib.parse import quote_plus
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

def _normalize_db_url(url: str) -> str:
    for prefix in ('postgres://', 'postgresql://'):
        if url.startswith(prefix):
            return 'postgresql+psycopg2://' + url[len(prefix):]
    return url

def create_app(config_class=None):

    app = Flask(__name__)  # NOSONAR — REST API JWT stateless, pas de sessions cookie → CSRF sans objet

    # 1. Charger la config de base EN PREMIER
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object(config.Config)

    # 2. Configurer la DB APRÈS (pour ne pas être écrasé par from_object)
    _database_url = os.environ.get('DATABASE_URL', '').strip()
    if _database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = _normalize_db_url(_database_url)
    elif os.environ.get('PGHOST'):
        _pg_user     = os.environ.get('PGUSER',     'postgres')
        _pg_password = quote_plus(os.environ.get('PGPASSWORD', ''))
        _pg_host     = os.environ.get('PGHOST',     'localhost')
        _pg_port     = os.environ.get('PGPORT',     '5432')
        _pg_db       = os.environ.get('PGDATABASE', 'oliboBd')
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f"postgresql+psycopg2://{_pg_user}:{_pg_password}"
            f"@{_pg_host}:{_pg_port}/{_pg_db}"
        )
    else:
        _pg = config.Config.POSTGRESQL_CONNEXION
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f"postgresql+psycopg2://{_pg['user']}:{quote_plus(_pg['password'])}"
            f"@{_pg['host']}:{_pg['port']}/{_pg['database']}?sslmode=disable"
        )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 3. Surcharger les clés sensibles depuis l'environnement
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY'))  # NOSONAR
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config.get('JWT_SECRET_KEY'))  # NOSONAR
    app.config['JWT_TOKEN_LOCATION'] = app.config.get('JWT_TOKEN_LOCATION', config.Config.JWT_TOKEN_LOCATION)
    app.config['JWT_HEADER_NAME'] = app.config.get('JWT_HEADER_NAME', config.Config.JWT_HEADER_NAME)
    app.config['JWT_HEADER_TYPE'] = app.config.get('JWT_HEADER_TYPE', config.Config.JWT_HEADER_TYPE)
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_SESSION_COOKIE'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    # 4. CORS
    _cors_env = os.environ.get('CORS_ORIGINS', 'http://localhost:4200')
    _cors_origins = [o.strip() for o in _cors_env.split(',')]
    CORS(app,
         resources={r"/api/*": {"origins": _cors_origins}},
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"]
    )

    # 5. Cloudinary
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET')
    )

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

        @app.route("/", methods=['GET'])
        def test():
            return "API is running"

        swagger_path = os.path.join(os.path.dirname(app.root_path), 'swagger.yaml')
        with open(swagger_path, 'r', encoding='utf-8') as f:
            swagger_template = yaml.safe_load(f)
        Swagger(app, template=swagger_template)

        db.create_all()

    return app