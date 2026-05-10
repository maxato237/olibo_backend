import os
from urllib.parse import quote_plus

import boto3
from dotenv import load_dotenv

load_dotenv()

class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY')  # NOSONAR
    SECRET_JWT_KEY = os.environ.get('JWT_SECRET_KEY')  # NOSONAR
    DEBUG = True
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    from urllib.parse import quote_plus
    import os

    def get_db_password(self):
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

    def get_database_uri(self):
        host = os.environ['PGHOST']
        user = os.environ['PGUSER']
        database = os.environ.get('PGDATABASE', 'postgres')
        port = os.environ.get('PGPORT', '5432')
        password = quote_plus(self.get_db_password())  # token encodé comme mot de passe

        return (
            f"postgresql://{user}:{password}"
            f"@{host}:{port}/{database}"
            f"?sslmode=disable"
        )

    POSTGRESQL_CONNEXION = {
        'host': os.environ.get('LOCAL_DB_HOST', 'localhost'),
        'user': os.environ.get('LOCAL_DB_USER', 'postgres'),
        'password': os.environ.get('LOCAL_DB_PASSWORD', ''),
        'database': os.environ.get('LOCAL_DB_NAME', 'oliboBd'),
        'port': os.environ.get('LOCAL_DB_PORT', '5432'),
    }

    DISTANT_DB_CONNEXION = {
        'host': os.environ.get('PGHOST', ''),
        'user': os.environ.get('PGUSER', ''),
        'password': os.environ.get('PGPASSWORD', ''),
        'database': os.environ.get('PGDATABASE', 'postgres'),
        'port': int(os.environ.get('PGPORT', 5432)),
        'sslmode': os.environ.get('PGSSLMODE', 'require'),
    }