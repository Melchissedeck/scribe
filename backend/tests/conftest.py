# Fixtures pytest partagees : basculent l'application sur une base SQLite en
# memoire pour que les tests n'aient jamais besoin d'une base Postgres reelle.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  # enregistre tous les modeles sur Base.metadata
from app.database import Base, get_db
from app.main import app as fastapi_app

TEST_DATABASE_URL = 'sqlite:///:memory:'

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={'check_same_thread': False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    # Cree un schema propre pour chaque test, et le detruit juste apres
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    # Remplace la dependance get_db par la session de test SQLite
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
