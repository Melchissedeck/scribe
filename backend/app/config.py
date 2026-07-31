# Configuration centralisee de l'application, lue depuis les variables d'environnement

import os


class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'postgresql://scribe:scribe@localhost:5432/scribe')


settings = Settings()
