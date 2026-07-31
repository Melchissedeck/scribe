# Configuration centralisee de l'application, lue depuis les variables d'environnement

import os


class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'postgresql://scribe:scribe@localhost:5432/scribe')
    jwt_secret_key: str = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')
    jwt_algorithm: str = 'HS256'
    jwt_expiration_minutes: int = 60
    allowed_origin: str = os.getenv('ALLOWED_ORIGIN', 'http://127.0.0.1:5500')


settings = Settings()
