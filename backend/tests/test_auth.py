from datetime import datetime, timedelta

import pytest
from jose import jwt

from app.config import settings
from app.exceptions import InvalidCredentialsError, TokenExpiredError
from app.services.jwt import create_access_token, decode_access_token

# ── Inscription ──────────────────────────────────────────────────────────

def test_register_creates_user(client):
    response = client.post('/auth/register', json={
        'name': 'Alice',
        'email': 'alice@example.com',
        'password': 'testpass123',
    })

    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'Alice'
    assert data['email'] == 'alice@example.com'
    assert 'id' in data
    assert 'hashed_password' not in data


def test_register_rejects_duplicate_email(client):
    client.post('/auth/register', json={
        'name': 'Alice',
        'email': 'dup@example.com',
        'password': 'testpass123',
    })

    response = client.post('/auth/register', json={
        'name': 'Bob',
        'email': 'dup@example.com',
        'password': 'anotherpass',
    })

    assert response.status_code == 400
    assert response.json()['detail'] == 'Cet email est deja utilise'


# ── Connexion ────────────────────────────────────────────────────────────

def test_login_returns_token_for_valid_credentials(client):
    client.post('/auth/register', json={
        'name': 'Carol',
        'email': 'carol@example.com',
        'password': 'testpass123',
    })

    response = client.post('/auth/login', json={
        'email': 'carol@example.com',
        'password': 'testpass123',
    })

    assert response.status_code == 200
    data = response.json()
    assert data['token_type'] == 'bearer'
    assert data['access_token']


def test_login_rejects_wrong_password(client):
    client.post('/auth/register', json={
        'name': 'Dan',
        'email': 'dan@example.com',
        'password': 'testpass123',
    })

    response = client.post('/auth/login', json={
        'email': 'dan@example.com',
        'password': 'wrongpass',
    })

    assert response.status_code == 401
    assert response.json()['detail'] == 'Email ou mot de passe incorrect'


def test_login_rejects_unknown_email(client):
    response = client.post('/auth/login', json={
        'email': 'ghost@example.com',
        'password': 'whatever123',
    })

    assert response.status_code == 401
    assert response.json()['detail'] == 'Email ou mot de passe incorrect'


# ── Token JWT ────────────────────────────────────────────────────────────

def test_create_and_decode_access_token_round_trip():
    token = create_access_token(user_id=42)

    assert decode_access_token(token) == 42


def test_decode_access_token_raises_on_expired_token():
    expired_payload = {'sub': '1', 'exp': datetime.utcnow() - timedelta(minutes=5)}
    token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(TokenExpiredError):
        decode_access_token(token)


def test_decode_access_token_raises_on_malformed_token():
    with pytest.raises(InvalidCredentialsError):
        decode_access_token('token.completement.invalide')
