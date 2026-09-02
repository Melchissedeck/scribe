from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.action import Action
from app.models.recording import Recording
from app.models.speaker import Speaker
from app.models.transcript_segment import TranscriptSegment
from app.schemas.llm_summary import SegmentClassification, SegmentClassificationResult


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


# ── list_meetings ────────────────────────────────────────────────────────

def test_list_meetings_returns_empty_when_none(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings', headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_meetings_filters_by_theme_and_date(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()

    now = datetime.utcnow()
    matching = _create_recording(db_session, user.id, theme='Sprint Planning', started_at=now)
    _create_recording(db_session, user.id, theme='Autre sujet', started_at=now)
    _create_recording(db_session, user.id, theme='Sprint Review', started_at=now - timedelta(days=10))

    resp = client.get('/meetings', params={'theme': 'sprint', 'date_from': now.date().isoformat()}, headers=headers)

    assert resp.status_code == 200
    ids = [item['id'] for item in resp.json()]
    assert ids == [matching.id]


def test_list_meetings_requires_auth(client):
    resp = client.get('/meetings')
    assert resp.status_code == 401


# ── update_meeting_theme ─────────────────────────────────────────────────

def test_update_meeting_theme_sets_and_clears(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    resp = client.patch(f'/meetings/{recording.id}/theme', json={'theme': '  Nouveau thème  '}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['theme'] == 'Nouveau thème'

    resp = client.patch(f'/meetings/{recording.id}/theme', json={'theme': '   '}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['theme'] is None


def test_update_meeting_theme_returns_404_when_not_owner(client, db_session):
    headers = _auth_headers(client)
    other = _create_recording(db_session, user_id=9999)

    resp = client.patch(f'/meetings/{other.id}/theme', json={'theme': 'x'}, headers=headers)
    assert resp.status_code == 404


# ── speaking-time ────────────────────────────────────────────────────────

def test_get_speaking_time_computes_percentages(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    db_session.add_all([
        TranscriptSegment(recording_id=recording.id, start=0.0, end=6.0, text='a', speaker='Alice'),
        TranscriptSegment(recording_id=recording.id, start=6.0, end=8.0, text='b', speaker='Bob'),
    ])
    db_session.commit()

    resp = client.get(f'/meetings/{recording.id}/speaking-time', headers=headers)

    assert resp.status_code == 200
    entries = resp.json()['entries']
    assert entries[0]['speaker'] == 'Alice'
    assert entries[0]['percentage'] == 75.0
    assert entries[1]['percentage'] == 25.0


def test_get_speaking_time_returns_empty_entries_without_segments(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    resp = client.get(f'/meetings/{recording.id}/speaking-time', headers=headers)

    assert resp.status_code == 200
    assert resp.json()['entries'] == []


def test_get_speaking_time_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings/999/speaking-time', headers=headers)
    assert resp.status_code == 404


# ── diarized-transcript ──────────────────────────────────────────────────

def test_get_diarized_transcript_returns_segments(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)
    db_session.add(TranscriptSegment(recording_id=recording.id, start=0.0, end=1.0, text='Bonjour', speaker='Alice'))
    db_session.commit()

    resp = client.get(f'/meetings/{recording.id}/diarized-transcript', headers=headers)

    assert resp.status_code == 200
    assert resp.json()['segments'] == [{'speaker_name': 'Alice', 'text': 'Bonjour', 'start': None}]


def test_get_diarized_transcript_returns_404_without_segments(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    resp = client.get(f'/meetings/{recording.id}/diarized-transcript', headers=headers)
    assert resp.status_code == 404


def test_get_diarized_transcript_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings/999/diarized-transcript', headers=headers)
    assert resp.status_code == 404


# ── classify-segments ────────────────────────────────────────────────────

def test_classify_segments_updates_segments(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)
    seg = TranscriptSegment(recording_id=recording.id, start=0.0, end=1.0, text='Bonjour', speaker='Alice')
    db_session.add(seg)
    db_session.commit()
    db_session.refresh(seg)

    fake_result = SegmentClassificationResult(
        classifications=[SegmentClassification(index=0, tone='neutre', theme='ouverture', urgency='faible')]
    )
    with patch('app.routes.meetings.LLMService') as mock_cls:
        mock_cls.return_value.classify_segments.return_value = fake_result
        resp = client.post(f'/meetings/{recording.id}/classify-segments', headers=headers)

    assert resp.status_code == 200
    body = resp.json()['segments'][0]
    assert body['tone'] == 'neutre'
    assert body['theme'] == 'ouverture'
    assert body['urgency'] == 'faible'


def test_classify_segments_returns_400_without_segments(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    resp = client.post(f'/meetings/{recording.id}/classify-segments', headers=headers)
    assert resp.status_code == 400


def test_classify_segments_returns_502_when_llm_unavailable(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)
    db_session.add(TranscriptSegment(recording_id=recording.id, start=0.0, end=1.0, text='Bonjour', speaker='Alice'))
    db_session.commit()

    with patch('app.routes.meetings.LLMService') as mock_cls:
        mock_cls.return_value.classify_segments.return_value = None
        resp = client.post(f'/meetings/{recording.id}/classify-segments', headers=headers)

    assert resp.status_code == 502


def test_classify_segments_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.post('/meetings/999/classify-segments', headers=headers)
    assert resp.status_code == 404


# ── segments-classification ──────────────────────────────────────────────

def test_get_segments_classification_returns_saved_values(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)
    db_session.add(TranscriptSegment(
        recording_id=recording.id, start=0.0, end=1.0, text='Bonjour', speaker='Alice',
        tone='neutre', theme='ouverture', urgency='faible',
    ))
    db_session.commit()

    resp = client.get(f'/meetings/{recording.id}/segments-classification', headers=headers)

    assert resp.status_code == 200
    assert resp.json()['segments'][0]['tone'] == 'neutre'


def test_get_segments_classification_returns_404_without_segments(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    resp = client.get(f'/meetings/{recording.id}/segments-classification', headers=headers)
    assert resp.status_code == 404


def test_get_segments_classification_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings/999/segments-classification', headers=headers)
    assert resp.status_code == 404


# ── anonymize ─────────────────────────────────────────────────────────────

def test_anonymize_meeting_renames_speakers(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)
    db_session.add(Speaker(recording_id=recording.id, provisional_name='Alice Dupont'))
    db_session.add(TranscriptSegment(recording_id=recording.id, start=0.0, end=1.0, text='Bonjour', speaker='Alice Dupont'))
    db_session.commit()

    resp = client.post(f'/meetings/{recording.id}/anonymize', headers=headers)

    assert resp.status_code == 200
    assert resp.json()['segments'][0]['speaker_name'] == 'Locuteur 1'


def test_anonymize_meeting_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.post('/meetings/999/anonymize', headers=headers)
    assert resp.status_code == 404


# ── details ───────────────────────────────────────────────────────────────

def test_get_meeting_details_returns_full_payload(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id, theme='Point hebdo')
    speaker = Speaker(recording_id=recording.id, provisional_name='Alice')
    db_session.add(speaker)
    db_session.commit()
    db_session.refresh(speaker)
    db_session.add(TranscriptSegment(recording_id=recording.id, start=0.0, end=1.0, text='Bonjour', speaker='Alice'))
    db_session.add(Action(recording_id=recording.id, speaker_id=speaker.id, description='Faire X', status='todo'))
    db_session.commit()

    resp = client.get(f'/meetings/{recording.id}/details', headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body['theme'] == 'Point hebdo'
    assert body['meeting_type'] == 'in_person'
    assert body['diarization_status'] == 'done'
    assert len(body['speakers']) == 1
    assert len(body['segments']) == 1
    assert len(body['actions']) == 1


def test_get_meeting_details_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings/999/details', headers=headers)
    assert resp.status_code == 404


# ── delete ───────────────────────────────────────────────────────────────

def test_delete_meeting_removes_recording(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    resp = client.delete(f'/meetings/{recording.id}', headers=headers)
    assert resp.status_code == 204

    assert db_session.query(Recording).filter(Recording.id == recording.id).first() is None


def test_delete_meeting_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.delete('/meetings/999', headers=headers)
    assert resp.status_code == 404


# ── export-pdf ───────────────────────────────────────────────────────────

def test_export_meeting_pdf_returns_pdf_bytes(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id)

    with patch('app.routes.meetings.PDFExportService') as mock_cls:
        mock_cls.return_value.generate_pdf.return_value = b'%PDF-1.4 fake'
        resp = client.get(f'/meetings/{recording.id}/export-pdf', headers=headers)

    assert resp.status_code == 200
    assert resp.content == b'%PDF-1.4 fake'
    assert resp.headers['content-type'] == 'application/pdf'


def test_export_meeting_pdf_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings/999/export-pdf', headers=headers)
    assert resp.status_code == 404


# ── export-docx ──────────────────────────────────────────────────────────

def test_export_docx_includes_action_table(client, db_session):
    headers = _auth_headers(client)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == 'test@example.com').first()
    recording = _create_recording(db_session, user.id, theme='Point hebdo', summary='## Résumé\n- point un')
    speaker = Speaker(recording_id=recording.id, provisional_name='Alice')
    db_session.add(speaker)
    db_session.commit()
    db_session.refresh(speaker)
    db_session.add(Action(recording_id=recording.id, speaker_id=speaker.id, description='Faire X', status='todo'))
    db_session.commit()

    resp = client.get(f'/meetings/{recording.id}/export-docx', headers=headers)

    assert resp.status_code == 200
    assert resp.headers['content-type'] == (
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    assert len(resp.content) > 0


def test_export_docx_returns_404_when_not_found(client):
    headers = _auth_headers(client)
    resp = client.get('/meetings/999/export-docx', headers=headers)
    assert resp.status_code == 404
