# Connexion a la base de donnees PostgreSQL via SQLAlchemy

import os

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"client_encoding": "utf8"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    # Dependance FastAPI fournissant une session de base de donnees par requete
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
