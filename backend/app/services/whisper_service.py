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

        # Les stubs du SDK Groq typent .create() comme renvoyant toujours un
        # objet Transcription, quel que soit response_format ; avec "text" il
        # renvoie en realite directement une chaine.
        return transcription  # type: ignore[return-value]

    def transcribe_segments(self, audio_path: str) -> list[dict]:
        with open(audio_path, "rb") as audio_file:
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