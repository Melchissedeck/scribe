# US-69 : anonymisation des locuteurs d'une reunion (droit a l'effacement RGPD)

from app.models.recording import Recording
from app.models.speaker import Speaker
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.services.anonymization_service import anonymize_recording


def _make_recording(db_session, real_speaker_names: list[str]) -> Recording:
    user = User(name='Test', email='anonymize-test@example.com', hashed_password='x')
    db_session.add(user)
    db_session.flush()

    recording = Recording(
        user_id=user.id,
        platform='google_meet',
        native_meeting_id='abc-defg-hij',
    )
    db_session.add(recording)
    db_session.flush()

    for name in real_speaker_names:
        db_session.add(Speaker(recording_id=recording.id, provisional_name=name, real_name=name))
        db_session.add(TranscriptSegment(
            recording_id=recording.id,
            speaker=name,
            text=f'Bonjour, je suis {name}.',
            start=0.0,
            end=5.0,
        ))

    db_session.commit()
    return recording


def test_anonymize_recording_replaces_speaker_and_segment_names(db_session):
    recording = _make_recording(db_session, ['Jean Dupont', 'Marie Curie'])

    anonymize_recording(db_session, recording.id)

    speakers = db_session.query(Speaker).filter(Speaker.recording_id == recording.id).order_by(Speaker.id).all()
    segments = (
        db_session.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == recording.id)
        .order_by(TranscriptSegment.id)
        .all()
    )

    assert [s.provisional_name for s in speakers] == ['Locuteur 1', 'Locuteur 2']
    assert all(s.real_name is None for s in speakers)
    assert [seg.speaker for seg in segments] == ['Locuteur 1', 'Locuteur 2']
    # Le texte des segments (contenu de la transcription) n'est pas touché :
    # seule l'attribution du locuteur est anonymisée, pas le contenu parlé.
    assert segments[0].text == 'Bonjour, je suis Jean Dupont.'


def test_anonymize_recording_is_a_noop_without_speakers(db_session):
    # Une réunion dictaphone n'a pas de table Speaker associée (labels déjà
    # génériques type SPEAKER_00 issus de Pyannote) : rien à anonymiser.
    recording = _make_recording(db_session, [])
    db_session.add(TranscriptSegment(
        recording_id=recording.id, speaker='SPEAKER_00', text='Salut.', start=0.0, end=2.0,
    ))
    db_session.commit()

    anonymize_recording(db_session, recording.id)

    segment = (
        db_session.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == recording.id)
        .first()
    )
    assert segment.speaker == 'SPEAKER_00'


def test_anonymize_meeting_route_requires_ownership(client, db_session):
    recording = _make_recording(db_session, ['Jean Dupont'])

    client.post('/auth/register', json={
        'name': 'Other', 'email': 'other@example.com', 'password': 'testpass123',
    })
    other_login = client.post('/auth/login', json={
        'email': 'other@example.com', 'password': 'testpass123',
    })
    other_headers = {'Authorization': f'Bearer {other_login.json()["access_token"]}'}

    response = client.post(f'/meetings/{recording.id}/anonymize', headers=other_headers)

    assert response.status_code == 404
