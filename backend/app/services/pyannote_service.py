import os
import subprocess
import tempfile
from pathlib import Path

from app.config import settings


# Windows : rendre les DLL FFmpeg visibles à torchcodec
# avant d'importer pyannote.
if os.name == "nt":
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
            output = self.pipeline(wav_path)

            return [
                {
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                }
                for turn, speaker in output.speaker_diarization
            ]

        finally:
            Path(wav_path).unlink(missing_ok=True)