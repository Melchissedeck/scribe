import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

# Windows : rendre les DLL FFmpeg visibles à torchcodec avant d'importer
# pyannote. sys.platform (plutot que os.name) : mypy reconnait cette forme
# specifiquement et exclut la branche de l'analyse sur les autres OS, ce qui
# evite une erreur "os.add_dll_directory n'existe pas" quand mypy tourne sur
# Linux (CI) tout en restant verifie normalement sous Windows.
if sys.platform == "win32":
    if settings.ffmpeg_bin:
        ffmpeg_bin = Path(settings.ffmpeg_bin)

        if ffmpeg_bin.is_dir():
            os.add_dll_directory(str(ffmpeg_bin))


from pyannote.audio import Pipeline


class PyannoteService:

    def __init__(self):
        if not settings.pyannote_auth_token:
            raise ValueError(
                "PYANNOTE_AUTH_TOKEN is not configured"
            )

        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1",
            token=settings.pyannote_auth_token,
        )

    def _to_wav(self, audio_path: str) -> str:
        """
        Convertit le fichier audio en WAV 16 kHz mono.

        MediaRecorder produit généralement du WebM.
        Certains fichiers WebM peuvent avoir des métadonnées
        de durée incomplètes, ce qui pose problème à Pyannote.

        FFmpeg reconstruit un fichier WAV avec un header
        contenant correctement les informations audio.
        """

        ffmpeg = "ffmpeg"

        if settings.ffmpeg_bin:
            ffmpeg = str(Path(settings.ffmpeg_bin) / "ffmpeg")

        output_path = (
            Path(tempfile.gettempdir())
            / f"{Path(audio_path).stem}_16k.wav"
        )

        try:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    audio_path,
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-f",
                    "wav",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "Erreur FFmpeg lors de la conversion audio : "
                f"{exc.stderr}"
            ) from exc

        return str(output_path)

    def diarize(self, audio_path: str) -> list[dict]:
        """
        Effectue la diarisation du fichier audio.

        Le fichier original est d'abord converti en WAV 16 kHz mono.
        Pyannote travaille ensuite sur le fichier WAV temporaire.

        Le fichier temporaire est supprimé après la diarisation.
        """

        wav_path = self._to_wav(audio_path)

        try:
            # Stubs pyannote.audio imprecis : Pipeline.from_pretrained() est
            # type comme pouvant renvoyer None, et l'objet retourne par un
            # appel du pipeline n'expose pas .speaker_diarization dans ses
            # stubs alors qu'il l'expose reellement a l'execution.
            output = self.pipeline(wav_path)  # type: ignore[misc]

            return [
                {
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                }
                for turn, speaker in output.speaker_diarization  # type: ignore[union-attr]
            ]

        finally:
            Path(wav_path).unlink(missing_ok=True)


def get_pyannote_service(app: "FastAPI") -> PyannoteService:
    """Retourne le PyannoteService de l'application, en le créant au besoin.

    Le pipeline pyannote (torch + poids du modèle) n'est chargé qu'au
    premier appel, pas au démarrage de l'application, pour ne pas
    pénaliser le temps de démarrage ni la mémoire disponible pour les
    autres routes tant que la diarisation dictaphone n'est pas utilisée.

    Args:
        app: Instance FastAPI, dont l'état porte la référence mise en cache.

    Returns:
        Le PyannoteService partagé par l'application.
    """
    if app.state.pyannote_service is None:
        app.state.pyannote_service = PyannoteService()
    return app.state.pyannote_service