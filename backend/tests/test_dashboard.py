from app.models.recording import Recording
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User


def _auth_headers(client, email='test@example.com'):
    client.post('/auth/register', json={
        'name': 'Test',
        'email': email,
        'password': 'testpass123',
    })
    resp = client.post('/auth/login', json={
        'email': email,
        'password': 'testpass123',
    })
    return {'Authorization': f'Bearer {resp.json()["access_token"]}'}


def _create_recording(db_session, user_id, **overrides):
    defaults = {
        'user_id': user_id,
        'platform': 'dictaphone',
        'native_meeting_id': 'local',
        'status': 'stopped',
        'diarization_status': 'done',
    }
    defaults.update(overrides)
    recording = Recording(**defaults)
    db_session.add(recording)
    db_session.commit()
    db_session.refresh(recording)
    return recording


# ── speaking-time (dashboard aggregate) ─────────────────────────────────

def test_get_dashboard_speaking_time_returns_empty_without_segments(client):
    headers = _auth_headers(client)
    resp = client.get('/dashboard/speaking-time', headers=headers)
    assert resp.status_code == 200
    assert resp.json()['entries'] == []


def test_get_dashboard_speaking_time_aggregates_across_meetings(client, db_session):
    headers = _auth_headers(client)
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording_1 = _create_recording(db_session, user.id)
    recording_2 = _create_recording(db_session, user.id)

    db_session.add_all([
        TranscriptSegment(recording_id=recording_1.id, start=0.0, end=6.0, text='a', speaker='Alice'),
        TranscriptSegment(recording_id=recording_1.id, start=6.0, end=8.0, text='b', speaker='Bob'),
        TranscriptSegment(recording_id=recording_2.id, start=0.0, end=6.0, text='c', speaker='Alice'),
    ])
    db_session.commit()

    resp = client.get('/dashboard/speaking-time', headers=headers)

    assert resp.status_code == 200
    entries = {e['speaker']: e for e in resp.json()['entries']}
    assert entries['Alice']['seconds'] == 12.0
    assert entries['Bob']['seconds'] == 2.0
    assert entries['Alice']['percentage'] == 85.7


def test_get_dashboard_speaking_time_excludes_other_users(client, db_session):
    headers_a = _auth_headers(client, email='a@example.com')
    _auth_headers(client, email='b@example.com')

    user_b = db_session.query(User).filter(User.email == 'b@example.com').first()
    recording_b = _create_recording(db_session, user_b.id)
    db_session.add(TranscriptSegment(recording_id=recording_b.id, start=0.0, end=10.0, text='x', speaker='Charlie'))
    db_session.commit()

    resp = client.get('/dashboard/speaking-time', headers=headers_a)

    assert resp.status_code == 200
    assert resp.json()['entries'] == []
