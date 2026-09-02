from unittest.mock import patch

from app.models.recording import Recording
from app.models.user import User
from app.services.audio_capture_service import run_capture_background_job


def _create_user(db_session):
    user = User(name='Test', email='capture@example.com', hashed_password='x')
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_recording(db_session, user_id, **overrides):
    defaults = {
        'user_id': user_id,
        'platform': 'dictaphone',
        'native_meeting_id': 'local',
        'status': 'stopped',
    }
    defaults.update(overrides)
    recording = Recording(**defaults)
    db_session.add(recording)
    db_session.commit()
    db_session.refresh(recording)
    return recording


@patch('app.services.audio_capture_service.run_post_meeting_processing')
@patch('app.services.audio_capture_service.SessionLocal')
def test_run_capture_background_job_runs_post_processing_on_success(mock_session_local, mock_post_processing, db_session):
    mock_session_local.return_value = db_session
    user = _create_user(db_session)
    recording = _create_recording(db_session, user.id)

    run_capture_background_job(recording.id, lambda db, rec: True)

    mock_post_processing.assert_called_once_with(recording.id)


@patch('app.services.audio_capture_service.run_post_meeting_processing')
@patch('app.services.audio_capture_service.SessionLocal')
def test_run_capture_background_job_skips_post_processing_on_failure(mock_session_local, mock_post_processing, db_session):
    mock_session_local.return_value = db_session
    user = _create_user(db_session)
    recording = _create_recording(db_session, user.id)

    run_capture_background_job(recording.id, lambda db, rec: False)

    mock_post_processing.assert_not_called()


@patch('app.services.audio_capture_service.run_post_meeting_processing')
@patch('app.services.audio_capture_service.SessionLocal')
def test_run_capture_background_job_handles_missing_recording(mock_session_local, mock_post_processing, db_session):
    mock_session_local.return_value = db_session
    calls = []

    def process(db, rec):
        calls.append(rec)
        return True

    run_capture_background_job(999, process)

    assert calls == []
    mock_post_processing.assert_not_called()


@patch('app.services.audio_capture_service.run_post_meeting_processing')
@patch('app.services.audio_capture_service.SessionLocal')
def test_run_capture_background_job_passes_db_and_recording_to_process(mock_session_local, mock_post_processing, db_session):
    mock_session_local.return_value = db_session
    user = _create_user(db_session)
    recording = _create_recording(db_session, user.id)
    received = {}

    def process(db, rec):
        received['db'] = db
        received['recording_id'] = rec.id
        return True

    run_capture_background_job(recording.id, process)

    assert received['db'] is db_session
    assert received['recording_id'] == recording.id
