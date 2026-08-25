from unittest.mock import MagicMock, patch

from app.exceptions import VexaConnectionError, VexaInvalidMeetingError

MOCK_SEGMENTS = [{'speaker': 'Speaker 1', 'text': 'Bonjour', 'start': 0.0, 'end': 1.0}]
MOCK_TRANSCRIPT = 'Speaker 1 : Bonjour'

START_PAYLOAD = {
    'platform': 'google_meet',
    'native_meeting_id': 'abc123',
    'bot_name': 'Scribe',
    'meeting_url': 'https://meet.google.com/abc-xyz-123',
}


def _auth_headers(client):
    client.post('/auth/register', json={
        'name': 'Test',
        'email': 'test@example.com',
        'password': 'testpass123',
    })
    resp = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpass123',
    })
    return {'Authorization': f'Bearer {resp.json()["access_token"]}'}


def _start_session(client, headers, mock_agent):
    mock_agent.get_diarized_segments.return_value = MOCK_SEGMENTS
    mock_agent.get_transcript.return_value = MOCK_TRANSCRIPT
    resp = client.post('/recording/start', json=START_PAYLOAD, headers=headers)
    return resp


# ── Démarrage ─────────────────────────────────────────────────────────────

def test_start_recording_returns_active_session(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_cls.return_value = mock_agent

        resp = _start_session(client, headers, mock_agent)

    assert resp.status_code == 200
    assert resp.json()['status'] == 'active'
    assert resp.json()['platform'] == 'google_meet'
    mock_agent.send_bot.assert_called_once()


def test_start_recording_returns_503_when_vexa_unavailable(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_agent.send_bot.side_effect = VexaConnectionError()
        mock_cls.return_value = mock_agent

        resp = client.post('/recording/start', json=START_PAYLOAD, headers=headers)

    assert resp.status_code == 503
    assert 'indisponible' in resp.json()['detail']


def test_start_recording_returns_422_on_invalid_link(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_agent.send_bot.side_effect = VexaInvalidMeetingError()
        mock_cls.return_value = mock_agent

        resp = client.post('/recording/start', json={**START_PAYLOAD, 'meeting_url': 'invalide'}, headers=headers)

    assert resp.status_code == 422
    assert 'invalide' in resp.json()['detail']


def test_start_recording_requires_auth(client):
    resp = client.post('/recording/start', json=START_PAYLOAD)
    assert resp.status_code == 401


# ── Arrêt ─────────────────────────────────────────────────────────────────

def test_stop_recording_sets_status_stopped(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_cls.return_value = mock_agent

        recording_id = _start_session(client, headers, mock_agent).json()['id']
        resp = client.post(f'/recording/{recording_id}/stop', headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'stopped'
    assert data['transcript'] == MOCK_TRANSCRIPT


def test_stop_recording_returns_404_for_unknown_id(client):
    headers = _auth_headers(client)
    resp = client.post('/recording/9999/stop', headers=headers)
    assert resp.status_code == 404


def test_stop_recording_returns_400_if_already_stopped(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_cls.return_value = mock_agent

        recording_id = _start_session(client, headers, mock_agent).json()['id']
        client.post(f'/recording/{recording_id}/stop', headers=headers)
        resp = client.post(f'/recording/{recording_id}/stop', headers=headers)

    assert resp.status_code == 400


# ── Poll transcript ───────────────────────────────────────────────────────

def test_refresh_transcript_returns_transcript(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_cls.return_value = mock_agent

        recording_id = _start_session(client, headers, mock_agent).json()['id']
        resp = client.get(f'/recording/{recording_id}/transcript', headers=headers)

    assert resp.status_code == 200
    assert resp.json()['transcript'] == MOCK_TRANSCRIPT


def test_refresh_transcript_returns_503_when_vexa_unavailable(client):
    headers = _auth_headers(client)
    with patch('app.routes.recording.VexaAgent') as mock_cls:
        mock_agent = MagicMock()
        mock_cls.return_value = mock_agent

        recording_id = _start_session(client, headers, mock_agent).json()['id']
        mock_agent.get_diarized_segments.side_effect = VexaConnectionError()
        resp = client.get(f'/recording/{recording_id}/transcript', headers=headers)

    assert resp.status_code == 503
    assert 'indisponible' in resp.json()['detail']
