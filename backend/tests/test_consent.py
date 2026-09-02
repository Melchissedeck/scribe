# Consentement RGPD effectif côté serveur (audit reco #3)

from unittest.mock import MagicMock, patch


def _register_and_login(client, email='consent-test@example.com'):
    client.post('/auth/register', json={
        'name': 'Test', 'email': email, 'password': 'testpass123',
    })
    resp = client.post('/auth/login', json={'email': email, 'password': 'testpass123'})
    return {'Authorization': f'Bearer {resp.json()["access_token"]}'}


def test_consent_endpoint_records_timestamp(client):
    headers = _register_and_login(client)

    resp = client.post('/users/me/consent', headers=headers)

    assert resp.status_code == 200
    assert resp.json()['consent_given_at'] is not None


def test_dictaphone_recording_blocked_without_consent(client):
    headers = _register_and_login(client)

    resp = client.post('/meetings', headers=headers)

    assert resp.status_code == 403
    assert 'consentement' in resp.json()['detail'].lower()


def test_dictaphone_recording_allowed_after_consent(client):
    headers = _register_and_login(client)
    client.post('/users/me/consent', headers=headers)

    resp = client.post('/meetings', headers=headers)

    assert resp.status_code == 200


def test_visio_start_blocked_without_consent(client):
    headers = _register_and_login(client)

    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_cls.return_value = MagicMock()
        resp = client.post('/recording/start', headers=headers, json={
            'platform': 'google_meet',
            'native_meeting_id': 'abc123',
            'bot_name': 'Scribe',
            'meeting_url': 'https://meet.google.com/abc-xyz-123',
        })

    assert resp.status_code == 403
    mock_cls.return_value.send_bot.assert_not_called()


def test_consent_is_idempotent(client):
    headers = _register_and_login(client)

    first = client.post('/users/me/consent', headers=headers)
    second = client.post('/users/me/consent', headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
