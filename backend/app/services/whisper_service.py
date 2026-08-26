import math
import tempfile
from pathlib import Path

from groq import Groq
from pydub import AudioSegment

from app.config import settings

if settings.ffmpeg_bin:
    AudioSegment.converter = str(Path(settings.ffmpeg_bin) / "ffmpeg")

# Whisper (Groq) impose une limite de taille de fichier ; decouper les
# fichiers longs en tranches de 10 minutes reste largement en dessous,
# et borne le temps/la memoire de chaque appel.
_CHUNK_DURATION_MS = 10 * 60 * 1000


class WhisperService:

    def __init__(self):
        self.client = Groq(
            api_key=settings.groq_api_key
        )

    def transcribe(self, audio_path: str) -> str:
        chunks = self._split_audio(audio_path)
        try:
            texts = [self._transcribe_chunk_text(chunk_path) for _, chunk_path in chunks]
            return " ".join(text.strip() for text in texts if text.strip())
        finally:
            self._cleanup_chunks(chunks, audio_path)

    def transcribe_segments(self, audio_path: str) -> list[dict]:
        chunks = self._split_audio(audio_path)
        try:
            all_segments: list[dict] = []
            for offset_seconds, chunk_path in chunks:
                for segment in self._transcribe_chunk_segments(chunk_path):
                    all_segments.append({
                        "start": segment["start"] + offset_seconds,
                        "end": segment["end"] + offset_seconds,
                        "text": segment["text"],
                    })
            return all_segments
        finally:
            self._cleanup_chunks(chunks, audio_path)

    def _transcribe_chunk_text(self, chunk_path: Path) -> str:
        with open(chunk_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
                response_format="text",
            )

        # Les stubs du SDK Groq typent .create() comme renvoyant toujours un
        # objet Transcription, quel que soit response_format ; avec "text" il
        # renvoie en realite directement une chaine.
        return transcription  # type: ignore[return-value]

    def _transcribe_chunk_segments(self, chunk_path: Path) -> list[dict]:
        with open(chunk_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        return [
            {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
            }
            # Meme limitation de stub : la reponse verbose_json contient bien
            # un champ "segments" que le type Transcription ne declare pas.
            for segment in transcription.segments  # type: ignore[attr-defined]
        ]

    def _split_audio(self, audio_path: str) -> list[tuple[float, Path]]:
        """Decoupe le fichier en tranches de _CHUNK_DURATION_MS si necessaire.

        Retourne une liste de (offset_en_secondes, chemin_de_la_tranche). Un
        fichier deja assez court est retourne tel quel dans une liste a un
        seul element, sans creer de fichier temporaire.
        """
        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)

        if duration_ms <= _CHUNK_DURATION_MS:
            return [(0.0, Path(audio_path))]

        tmp_dir = Path(tempfile.mkdtemp(prefix="scribe_audio_chunks_"))
        chunk_count = math.ceil(duration_ms / _CHUNK_DURATION_MS)

        chunks: list[tuple[float, Path]] = []
        for index in range(chunk_count):
            start_ms = index * _CHUNK_DURATION_MS
            end_ms = min(start_ms + _CHUNK_DURATION_MS, duration_ms)
            chunk_path = tmp_dir / f"chunk_{index}.wav"
            audio[start_ms:end_ms].export(chunk_path, format="wav")
            chunks.append((start_ms / 1000, chunk_path))

        return chunks

    def _cleanup_chunks(self, chunks: list[tuple[float, Path]], original_path: str) -> None:
        for _, chunk_path in chunks:
            if str(chunk_path) != str(original_path):
                chunk_path.unlink(missing_ok=True)
