import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydub import AudioSegment

from app.services.speaker_assignment_service import SpeakerAssignmentService
from app.services.whisper_service import WhisperService


def _make_silence_wav(path: Path, duration_s: int, framerate: int = 8000) -> None:
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        wav_file.writeframes(b"\x00\x00" * framerate * duration_s)


# ── Recombinaison des segments après découpage audio (US-52) ───────────────

def test_transcribe_segments_recombines_chunks_with_correct_offsets(tmp_path):
    audio_path = tmp_path / "long.wav"
    _make_silence_wav(audio_path, duration_s=20 * 60)  # 20 min -> 3 tranches (8/8/4)

    fake_responses = [
        MagicMock(segments=[{"start": 0.0, "end": 5.0, "text": " Bonjour "}]),
        MagicMock(segments=[{"start": 1.0, "end": 6.0, "text": " ça va "}]),
        MagicMock(segments=[{"start": 2.0, "end": 4.0, "text": " au revoir "}]),
    ]

    with patch("app.services.whisper_service.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = fake_responses
        mock_groq_cls.return_value = mock_client

        segments = WhisperService().transcribe_segments(str(audio_path))

    assert segments == [
        {"start": 0.0, "end": 5.0, "text": "Bonjour"},
        {"start": 481.0, "end": 486.0, "text": "ça va"},
        {"start": 962.0, "end": 964.0, "text": "au revoir"},
    ]
    assert mock_client.audio.transcriptions.create.call_count == 3


def test_transcribe_recombines_chunk_texts_in_order(tmp_path):
    audio_path = tmp_path / "long.wav"
    _make_silence_wav(audio_path, duration_s=15 * 60)  # 15 min -> 2 tranches

    with patch("app.services.whisper_service.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = ["Bonjour.", "Au revoir."]
        mock_groq_cls.return_value = mock_client

        text = WhisperService().transcribe(str(audio_path))

    assert text == "Bonjour. Au revoir."


def test_split_audio_downsamples_chunks_to_16bit_even_when_source_is_32bit(tmp_path):
    # ffmpeg decode un WebM/Opus reel (MediaRecorder du navigateur) en
    # echantillons 32 bits par defaut. Sans un retour explicite a 16 bits,
    # chaque tranche exportee fait le double de la taille attendue et peut
    # depasser la limite de taille de Groq (413 Request Entity Too Large),
    # meme en restant sous le seuil de decoupage en duree.
    duration_s = 9 * 60  # > _CHUNK_DURATION_MS (8 min) -> decoupage en 2 tranches
    frame_rate = 8000
    sample_count = frame_rate * duration_s
    fake_audio = AudioSegment(
        data=b"\x00\x00\x00\x00" * sample_count,
        sample_width=4,
        frame_rate=frame_rate,
        channels=1,
    )

    audio_path = tmp_path / "recording.webm"
    audio_path.write_bytes(b"fake webm content")

    with patch("app.services.whisper_service.AudioSegment.from_file", return_value=fake_audio):
        chunks = WhisperService()._split_audio(str(audio_path))

    assert len(chunks) == 2
    for _, chunk_path in chunks:
        with wave.open(str(chunk_path), "rb") as wav_file:
            assert wav_file.getsampwidth() == 2


def test_transcribe_segments_does_not_split_short_audio(tmp_path):
    audio_path = tmp_path / "short.wav"
    _make_silence_wav(audio_path, duration_s=5)

    with patch("app.services.whisper_service.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = MagicMock(
            segments=[{"start": 0.0, "end": 2.0, "text": "Salut"}]
        )
        mock_groq_cls.return_value = mock_client

        segments = WhisperService().transcribe_segments(str(audio_path))

    assert segments == [{"start": 0.0, "end": 2.0, "text": "Salut"}]
    mock_client.audio.transcriptions.create.assert_called_once()
    # Un fichier court n'est jamais découpé : l'original ne doit pas être supprimé.
    assert audio_path.exists()


# ── Croisement des timestamps Whisper / Pyannote (US-35) ───────────────────

def test_assign_speakers_picks_matching_diarization_segment():
    transcription_segments = [
        {"start": 0.0, "end": 5.0, "text": "Bonjour"},
        {"start": 5.0, "end": 10.0, "text": "Comment ça va"},
    ]
    diarization_segments = [
        {"start": 0.0, "end": 4.5, "speaker": "SPEAKER_00"},
        {"start": 4.5, "end": 10.0, "speaker": "SPEAKER_01"},
    ]

    result = SpeakerAssignmentService().assign_speakers(transcription_segments, diarization_segments)

    assert result[0]["speaker"] == "SPEAKER_00"
    assert result[1]["speaker"] == "SPEAKER_01"


def test_assign_speakers_returns_fallback_when_no_overlap():
    # TranscriptSegment.speaker est NOT NULL en base : un segment sans
    # chevauchement doit recevoir une valeur de repli, jamais None.
    transcription_segments = [{"start": 100.0, "end": 105.0, "text": "..."}]
    diarization_segments = [{"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}]

    result = SpeakerAssignmentService().assign_speakers(transcription_segments, diarization_segments)

    assert result[0]["speaker"] == SpeakerAssignmentService.UNKNOWN_SPEAKER


def test_assign_speakers_picks_largest_overlap_on_chevauchement():
    # Chevauchement de parole : un segment de transcription chevauche deux
    # locuteurs, celui avec le plus grand recouvrement doit être retenu.
    transcription_segments = [{"start": 0.0, "end": 10.0, "text": "..."}]
    diarization_segments = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},  # 3s de recouvrement
        {"start": 3.0, "end": 10.0, "speaker": "SPEAKER_01"},  # 7s de recouvrement
    ]

    result = SpeakerAssignmentService().assign_speakers(transcription_segments, diarization_segments)

    assert result[0]["speaker"] == "SPEAKER_01"


# ── Fichier audio vide ou corrompu ──────────────────────────────────────────

def test_transcribe_segments_falls_back_when_pydub_cannot_read_file(tmp_path):
    """Un fichier illisible par pydub (ex. ffmpeg absent, contenu invalide) est
    transmis tel quel à Whisper plutôt que de faire échouer la transcription."""
    audio_path = tmp_path / "corrupted.wav"
    audio_path.write_bytes(b"not a real audio file")

    with patch("app.services.whisper_service.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = MagicMock(segments=[])
        mock_groq_cls.return_value = mock_client

        segments = WhisperService().transcribe_segments(str(audio_path))

    assert segments == []
    mock_client.audio.transcriptions.create.assert_called_once()


def test_transcribe_segments_propagates_error_when_whisper_rejects_audio(tmp_path):
    """Si Whisper rejette un fichier vide/corrompu, l'erreur remonte
    normalement (pas de blocage ni de plantage bas niveau)."""
    audio_path = tmp_path / "empty.wav"
    audio_path.write_bytes(b"")

    with patch("app.services.whisper_service.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("Invalid audio file")
        mock_groq_cls.return_value = mock_client

        with pytest.raises(Exception, match="Invalid audio file"):
            WhisperService().transcribe_segments(str(audio_path))


def test_transcribe_route_returns_502_on_corrupted_audio_without_crashing(client):
    client.post('/auth/register', json={
        'name': 'Test',
        'email': 'dictaphone-test@example.com',
        'password': 'testpass123',
    })
    login = client.post('/auth/login', json={
        'email': 'dictaphone-test@example.com',
        'password': 'testpass123',
    })
    headers = {'Authorization': f'Bearer {login.json()["access_token"]}'}

    create_resp = client.post('/meetings', headers=headers)
    recording_id = create_resp.json()['recording_id']

    client.post(
        f'/meetings/{recording_id}/upload-audio',
        headers=headers,
        files={'audio': ('corrupted.wav', b'not a real audio file', 'audio/wav')},
    )

    with patch('app.routes.dictaphone.WhisperService') as mock_service_cls:
        mock_service = MagicMock()
        mock_service.transcribe.side_effect = Exception('Invalid audio file')
        mock_service_cls.return_value = mock_service

        resp = client.post(f'/meetings/{recording_id}/transcribe', headers=headers)

    assert resp.status_code == 502
    assert 'Erreur lors de la transcription' in resp.json()['detail']
