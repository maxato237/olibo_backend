import os

import boto3

class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'PO2RxQLMzAMAnIZfRYbVtR8yfPPbfBSJ'
    SECRET_JWT_KEY = "0ee06252f7b14d3ea2463pf9d4s65j41"
    DEBUG = True
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Config email
    # MAIL_SERVER = 'smtp.gmail.com'
    # MAIL_PORT = 587
    # MAIL_USE_TLS = True
    # MAIL_USE_SSL = False
    # MAIL_USERNAME = 'melainenkeng@gmail.com'
    # MAIL_PASSWORD = 'vbpd ofhv muxm vhff'
    # MAIL_DEFAULT_SENDER = 'melainenkeng@gmail.com' 
    from urllib.parse import quote_plus
    import os

    def get_db_password():
        """Génère un token IAM temporaire (équivalent de signer.getAuthToken())"""
        client = boto3.client(
            'rds',
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        token = client.generate_db_auth_token(
            DBHostname=os.environ['PGHOST'],
            Port=int(os.environ.get('PGPORT', 5432)),
            DBUsername=os.environ['PGUSER'],
            Region=os.environ.get('AWS_REGION', 'us-east-1')
        )
        return token

    def get_database_uri():
        host = os.environ['PGHOST']
        user = os.environ['PGUSER']
        database = os.environ.get('PGDATABASE', 'postgres')
        port = os.environ.get('PGPORT', '5432')
        password = quote_plus(get_db_password())  # token encodé comme mot de passe

        return (
            f"postgresql://{user}:{password}"
            f"@{host}:{port}/{database}"
            f"?sslmode=require"
        )

    POSTGRESQL_CONNEXION = {
        'host': 'localhost',
        'user': 'postgres',
        'password': '12Monkeys#',
        'database': 'oliboBd',
        'port': '5432'
    }


    DISTANT_DB_CONNEXION = {
        'host': 'olibodb.cluster-cg18siw2sdzu.us-east-1.rds.amazonaws.com',      # PGHOST
        'user': 'postgres',          # PGUSER
        'password': 'TON_MOT_DE_PASSE', # à remplir
        'database': 'postgres',      # PGDATABASE
        'port': 5432,                # PGPORT
        'sslmode': 'require'         # PGSSLMODE
    }

# AWS_DB_CONNEXION = {
#     'host': 'database-1.cvu4s6ckuv7q.eu-north-1.rds.amazonaws.com',
#     'user': 'admin',
#     'password': '12Monkeys#',
#     'database': 'dinhosellerbd',
#     'port': '3306'
# }

# SQL_CONNEXION = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': '',
#     'database': 'dinhosellerbd',
#     'port': '3306'
# }




# class DevelopmentConfig(Config):
#     SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{SQL_CONNEXION['user']}:{SQL_CONNEXION['password']}@{SQL_CONNEXION['host']}/{SQL_CONNEXION['database']}"
#     SQLALCHEMY_TRACK_MODIFICATIONS = False


# class ProductionConfig(Config):
#     SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DISTANT_DB_CONNEXION['user']}:{DISTANT_DB_CONNEXION['password']}@{DISTANT_DB_CONNEXION['host']}/{DISTANT_DB_CONNEXION['database']}"
#     SQLALCHEMY_TRACK_MODIFICATIONS = False


# class TestingConfig(Config):
#     TESTING = True
#     SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
#     SQLALCHEMY_TRACK_MODIFICATIONS = False