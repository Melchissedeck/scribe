import requests
from app.config import settings


class VexaAgent:
    def __init__(self):
        self.base_url = "https://api.cloud.vexa.ai"
        self.headers = {
            "X-API-Key": settings.vexa_api_key,
            "Content-Type": "application/json",
        }

    def send_bot(self, platform: str, meeting_id: str, bot_name: str = "Scribe") -> dict:
        response = requests.post(
            f"{self.base_url}/bots",
            headers=self.headers,
            json={
                "platform": platform,
                "native_meeting_id": meeting_id,
                "bot_name": bot_name,
            },
        )
        response.raise_for_status()
        return response.json()

    def get_transcript(self, platform: str, meeting_id: str) -> str:
        response = requests.get(
            f"{self.base_url}/transcripts/{platform}/{meeting_id}",
            headers=self.headers,
        )
        response.raise_for_status()
        data = response.json()
        segments = data.get('segments', [])
        lines = []
        for seg in segments:
            speaker = seg.get('speaker', 'Inconnu')
            text = seg.get('text', '').strip()
            if text:
                lines.append(f'{speaker} : {text}')
        return '\n'.join(lines)

    def stop_bot(self, platform: str, meeting_id: str) -> int:
        response = requests.delete(
            f"{self.base_url}/bots/{platform}/{meeting_id}",
            headers=self.headers,
        )
        return response.status_code
