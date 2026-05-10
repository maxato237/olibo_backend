import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    SECRET_KEY     = os.environ.get('SECRET_KEY')       # NOSONAR
    SECRET_JWT_KEY = os.environ.get('JWT_SECRET_KEY')   # NOSONAR
    DEBUG          = os.environ.get('DEBUG', 'false').lower() == 'true'

    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME    = "Authorization"
    JWT_HEADER_TYPE    = "Bearer"

    # Utilisé uniquement en développement local (DATABASE_URL absent)
    POSTGRESQL_CONNEXION = {
        'host':     os.environ.get('LOCAL_DB_HOST',     'localhost'),
        'user':     os.environ.get('LOCAL_DB_USER',     'postgres'),
        'password': os.environ.get('LOCAL_DB_PASSWORD', ''),
        'database': os.environ.get('LOCAL_DB_NAME',     'oliboBd'),
        'port':     os.environ.get('LOCAL_DB_PORT',     '5432'),
    }