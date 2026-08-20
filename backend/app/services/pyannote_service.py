import os
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

    def diarize(self, audio_path: str) -> list[dict]:
        output = self.pipeline(audio_path)

        return [
            {
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker,
            }
            for turn, speaker in output.speaker_diarization
        ]