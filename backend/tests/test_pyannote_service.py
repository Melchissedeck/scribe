import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app.services import pyannote_service as pyannote_service_module
from app.services.pyannote_service import PyannoteService, get_pyannote_service


def _make_service(monkeypatch):
    monkeypatch.setattr(pyannote_service_module.settings, 'pyannote_auth_token', 'fake-token')
    with patch.object(pyannote_service_module.Pipeline, 'from_pretrained', return_value=MagicMock()):
        return PyannoteService()


def test_init_raises_when_token_missing(monkeypatch):
    monkeypatch.setattr(pyannote_service_module.settings, 'pyannote_auth_token', '')

    with pytest.raises(ValueError):
        PyannoteService()


def test_init_loads_pipeline_with_token(monkeypatch):
    monkeypatch.setattr(pyannote_service_module.settings, 'pyannote_auth_token', 'fake-token')

    with patch.object(pyannote_service_module.Pipeline, 'from_pretrained', return_value=MagicMock()) as mock_from_pretrained:
        service = PyannoteService()

    mock_from_pretrained.assert_called_once_with(
        'pyannote/speaker-diarization-community-1', token='fake-token'
    )
    assert service.pipeline is not None


def test_to_wav_returns_output_path_on_success(monkeypatch):
    service = _make_service(monkeypatch)
    monkeypatch.setattr(pyannote_service_module.settings, 'ffmpeg_bin', '')

    with patch.object(pyannote_service_module.subprocess, 'run') as mock_run:
        mock_run.return_value = MagicMock()
        output_path = service._to_wav('/tmp/recording.webm')

    assert output_path.endswith('recording_16k.wav')
    mock_run.assert_called_once()


def test_to_wav_raises_runtime_error_on_ffmpeg_failure(monkeypatch):
    service = _make_service(monkeypatch)
    monkeypatch.setattr(pyannote_service_module.settings, 'ffmpeg_bin', '')

    error = subprocess.CalledProcessError(1, ['ffmpeg'], stderr='conversion échouée')
    with patch.object(pyannote_service_module.subprocess, 'run', side_effect=error):
        with pytest.raises(RuntimeError, match='conversion échouée'):
            service._to_wav('/tmp/recording.webm')


def test_diarize_returns_turns_and_cleans_up_temp_file(monkeypatch):
    service = _make_service(monkeypatch)

    fake_turn_a = MagicMock(start=0.0, end=1.5)
    fake_turn_b = MagicMock(start=1.5, end=3.0)
    fake_output = MagicMock()
    fake_output.speaker_diarization = [(fake_turn_a, 'SPEAKER_00'), (fake_turn_b, 'SPEAKER_01')]
    service.pipeline = MagicMock(return_value=fake_output)

    with patch.object(service, '_to_wav', return_value='/tmp/recording_16k.wav'):
        with patch.object(pyannote_service_module.Path, 'unlink') as mock_unlink:
            result = service.diarize('/tmp/recording.webm')

    assert result == [
        {'start': 0.0, 'end': 1.5, 'speaker': 'SPEAKER_00'},
        {'start': 1.5, 'end': 3.0, 'speaker': 'SPEAKER_01'},
    ]
    mock_unlink.assert_called_once_with(missing_ok=True)


def test_get_pyannote_service_creates_and_caches_instance(monkeypatch):
    monkeypatch.setattr(pyannote_service_module.settings, 'pyannote_auth_token', 'fake-token')
    fake_app = MagicMock()
    fake_app.state.pyannote_service = None

    with patch.object(pyannote_service_module, 'PyannoteService') as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        first = get_pyannote_service(fake_app)
        fake_app.state.pyannote_service = first
        second = get_pyannote_service(fake_app)

    assert first is mock_instance
    assert second is mock_instance
    mock_cls.assert_called_once()
