import logging
import math
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from groq import APIConnectionError, APITimeoutError, Groq, InternalServerError, RateLimitError
from pydub import AudioSegment

from app.config import settings

if settings.ffmpeg_bin:
    AudioSegment.converter = str(Path(settings.ffmpeg_bin) / "ffmpeg")

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Erreurs transitoires (reseau, quota momentanement depasse, indisponibilite
# temporaire du service) qui justifient une nouvelle tentative. Les autres
# erreurs Groq (fichier invalide, cle API incorrecte...) ne sont jamais
# resolues par un retry et sont propagees immediatement.
_TRANSIENT_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_S = 1.0

# Whisper (Groq) impose une limite de taille de fichier (413 au-dela).
# Les tranches sont exportees en WAV mono 16 kHz 16 bits (format deja
# attendu par Whisper, et par Pyannote ailleurs dans le pipeline) plutot
# qu'a la frequence/nombre de canaux/largeur d'echantillon d'origine.
# Important : ffmpeg decode l'audio source (WebM/Opus du MediaRecorder du
# navigateur) en echantillons 32 bits par defaut ; set_channels() et
# set_frame_rate() seuls ne changent pas cette largeur, ce qui double la
# taille de fichier attendue (~29 Mo au lieu de ~15 Mo sur une tranche de
# 8 minutes, au-dessus de la limite). set_sample_width(2) force le retour
# a 16 bits. A 16 kHz mono 16 bits, 8 minutes restent confortablement sous
# la limite (~15 Mo) tout en bornant le temps/la memoire de chaque appel.
_CHUNK_DURATION_MS = 8 * 60 * 1000
_TARGET_FRAME_RATE = 16000
_TARGET_SAMPLE_WIDTH = 2


class WhisperService:

    def __init__(self):
        self.client = Groq(
            api_key=settings.groq_api_key
        )

    def transcribe(self, audio_path: str) -> str:
        """Transcrit un fichier audio en texte brut via Whisper (Groq).

        Découpe le fichier en tranches si nécessaire (voir `_split_audio`),
        transcrit chaque tranche puis recolle les textes obtenus.

        Args:
            audio_path: Chemin du fichier audio à transcrire.

        Returns:
            La transcription complète du fichier audio.

        Raises:
            RuntimeError: Si la transcription d'une tranche échoue après
                plusieurs tentatives (voir `_call_with_retry`).
        """
        chunks = self._split_audio(audio_path)
        try:
            texts = [self._transcribe_chunk_text(chunk_path) for _, chunk_path in chunks]
            return " ".join(text.strip() for text in texts if text.strip())
        finally:
            self._cleanup_chunks(chunks, audio_path)

    def transcribe_segments(self, audio_path: str) -> list[dict]:
        """Transcrit un fichier audio en segments horodatés via Whisper (Groq).

        Découpe le fichier en tranches si nécessaire (voir `_split_audio`),
        transcrit chaque tranche puis recale les horodatages de chaque
        segment obtenu sur le fichier d'origine (ajout de l'offset de la
        tranche).

        Args:
            audio_path: Chemin du fichier audio à transcrire.

        Returns:
            La liste des segments transcrits, chacun avec `start`, `end` et
            `text`, horodatés par rapport au fichier d'origine.

        Raises:
            RuntimeError: Si la transcription d'une tranche échoue après
                plusieurs tentatives (voir `_call_with_retry`).
        """
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
        def call() -> str:
            with open(chunk_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    response_format="text",
                )
            # Les stubs du SDK Groq typent .create() comme renvoyant toujours
            # un objet Transcription, quel que soit response_format ; avec
            # "text" il renvoie en realite directement une chaine.
            return transcription  # type: ignore[return-value]

        return self._call_with_retry(call)

    def _transcribe_chunk_segments(self, chunk_path: Path) -> list[dict]:
        def call() -> list[dict]:
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
                # Meme limitation de stub : la reponse verbose_json contient
                # bien un champ "segments" que le type Transcription ne
                # declare pas.
                for segment in transcription.segments  # type: ignore[attr-defined]
            ]

        return self._call_with_retry(call)

    def _call_with_retry(self, call: Callable[[], T]) -> T:
        """Execute `call`, avec reprise automatique sur erreur transitoire.

        Reessaie jusqu'a `_MAX_ATTEMPTS` fois avec un delai exponentiel
        (1s, 2s, 4s...) entre chaque tentative. Chaque tentative est
        logguee ; l'echec definitif leve une RuntimeError avec un message
        clair indiquant le nombre de tentatives effectuees.
        """
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return call()
            except _TRANSIENT_ERRORS as exc:
                last_exc = exc
                logger.warning(
                    "Erreur transitoire Whisper (tentative %d/%d) : %s",
                    attempt, _MAX_ATTEMPTS, exc,
                )
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(_RETRY_BASE_DELAY_S * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"La transcription a échoué après {_MAX_ATTEMPTS} tentatives : {last_exc}"
        ) from last_exc

    def _split_audio(self, audio_path: str) -> list[tuple[float, Path]]:
        """Decoupe le fichier en tranches de _CHUNK_DURATION_MS si necessaire.

        Retourne une liste de (offset_en_secondes, chemin_de_la_tranche). Un
        fichier deja assez court est retourne tel quel dans une liste a un
        seul element, sans creer de fichier temporaire.

        Si pydub/ffmpeg ne parvient pas a lire le fichier (ffmpeg absent,
        format non reconnu localement), le fichier est transmis tel quel a
        Whisper plutot que de faire echouer toute la transcription : avant
        le decoupage, l'envoi ne necessitait aucun traitement local.
        """
        try:
            audio = AudioSegment.from_file(audio_path)
        except Exception:
            return [(0.0, Path(audio_path))]

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
            chunk = (
                audio[start_ms:end_ms]
                .set_channels(1)
                .set_frame_rate(_TARGET_FRAME_RATE)
                .set_sample_width(_TARGET_SAMPLE_WIDTH)
            )
            chunk.export(chunk_path, format="wav")
            chunks.append((start_ms / 1000, chunk_path))

        return chunks

    def _cleanup_chunks(self, chunks: list[tuple[float, Path]], original_path: str) -> None:
        for _, chunk_path in chunks:
            if str(chunk_path) != str(original_path):
                chunk_path.unlink(missing_ok=True)
