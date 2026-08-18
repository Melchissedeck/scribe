from groq import Groq
from app.config import settings


class WhisperService:

    def __init__(self):
        self.client = Groq(
            api_key=settings.groq_api_key
        )

    def transcribe(self, audio_path: str) -> str:

        with open(audio_path, "rb") as audio_file:

            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
                response_format="text",
            )

        return transcription
