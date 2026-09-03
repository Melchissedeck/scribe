from unittest.mock import patch

from app.models.action import Action
from app.models.recording import Recording
from app.schemas.llm_summary import ActionItem, StructuredSummary
from app.services.action_extraction_service import run_action_extraction


def _create_recording(db_session, **overrides):
    defaults = {
        'user_id': 1,
        'platform': 'dictaphone',
        'native_meeting_id': 'local',
        'status': 'stopped',
        'transcript': 'Alice : il faut relire le document.',
    }
    defaults.update(overrides)
    recording = Recording(**defaults)
    db_session.add(recording)
    db_session.commit()
    db_session.refresh(recording)
    return recording


def _structured_summary():
    return StructuredSummary(
        themes=['Revue documentaire'],
        decisions=['Relire le document avant vendredi'],
        actions=[ActionItem(description='Relire le document', responsable='Alice', echeance=None)],
    )


@patch('app.services.action_extraction_service.LLMService')
def test_run_action_extraction_creates_actions(mock_llm_cls, db_session):
    mock_llm_cls.return_value.generate_structured_summary.return_value = _structured_summary()
    recording = _create_recording(db_session)

    created = run_action_extraction(db_session, recording)

    assert len(created) == 1
    assert created[0].description == 'Relire le document'
    assert db_session.query(Action).filter(Action.recording_id == recording.id).count() == 1


@patch('app.services.action_extraction_service.LLMService')
def test_run_action_extraction_is_idempotent(mock_llm_cls, db_session):
    # Reproduit le bug reel : deux appels concurrents (pipeline automatique
    # + fallback frontend) ne doivent jamais dupliquer les actions.
    mock_llm_cls.return_value.generate_structured_summary.return_value = _structured_summary()
    recording = _create_recording(db_session)

    first = run_action_extraction(db_session, recording)
    second = run_action_extraction(db_session, recording)

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id == second[0].id
    assert mock_llm_cls.return_value.generate_structured_summary.call_count == 1
    assert db_session.query(Action).filter(Action.recording_id == recording.id).count() == 1


@patch('app.services.action_extraction_service.LLMService')
def test_run_action_extraction_returns_empty_without_transcript(mock_llm_cls, db_session):
    recording = _create_recording(db_session, transcript=None)

    result = run_action_extraction(db_session, recording)

    assert result == []
    mock_llm_cls.return_value.generate_structured_summary.assert_not_called()
