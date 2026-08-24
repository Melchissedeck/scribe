import logging

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import settings
from app.exceptions import VexaConnectionError

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # secondes


class VexaAgent:
    def __init__(self):
        self.base_url = 'https://api.cloud.vexa.ai'
        self.headers = {
            'X-API-Key': settings.vexa_api_key,
            'Content-Type': 'application/json',
        }

    def send_bot(self, platform: str, meeting_id: str, bot_name: str = 'Scribe', meeting_url: str | None = None) -> dict:
        if meeting_url:
            payload: dict = {'meeting_url': meeting_url, 'bot_name': bot_name}
        else:
            payload = {'platform': platform, 'native_meeting_id': meeting_id, 'bot_name': bot_name}
        try:
            response = requests.post(
                f'{self.base_url}/bots',
                headers=self.headers,
                json=payload,
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (ConnectionError, Timeout) as exc:
            logger.error('Vexa - erreur de connexion (send_bot): %s', exc)
            raise VexaConnectionError() from exc
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 'inconnu'
            logger.error('Vexa - erreur HTTP %s (send_bot): %s', status_code, exc)
            raise VexaConnectionError(str(exc)) from exc

    def stop_bot(self, platform: str, meeting_id: str) -> int:
        try:
            response = requests.delete(
                f'{self.base_url}/bots/{platform}/{meeting_id}',
                headers=self.headers,
                timeout=_TIMEOUT,
            )
            return response.status_code
        except (ConnectionError, Timeout) as exc:
            logger.error('Vexa - erreur de connexion (stop_bot): %s', exc)
            raise VexaConnectionError() from exc
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 'inconnu'
            logger.error('Vexa - erreur HTTP %s (stop_bot): %s', status_code, exc)
            raise VexaConnectionError(str(exc)) from exc

    def get_transcript(self, platform: str, meeting_id: str) -> str:
        segments = self._fetch_segments(platform, meeting_id)
        lines = []
        for seg in segments:
            speaker = seg.get('speaker', 'Inconnu')
            text = seg.get('text', '').strip()
            if text:
                lines.append(f'{speaker} : {text}')
        return '\n'.join(lines)

    def get_diarized_segments(self, platform: str, meeting_id: str) -> list[dict]:
        """Retourne les segments bruts avec speaker label, text, start et end (secondes)."""
        return self._fetch_segments(platform, meeting_id)

    def _fetch_segments(self, platform: str, meeting_id: str) -> list[dict]:
        try:
            response = requests.get(
                f'{self.base_url}/transcripts/{platform}/{meeting_id}',
                headers=self.headers,
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            return response.json().get('segments', [])
        except (ConnectionError, Timeout) as exc:
            logger.error('Vexa - erreur de connexion (_fetch_segments): %s', exc)
            raise VexaConnectionError() from exc
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 'inconnu'
            logger.error('Vexa - erreur HTTP %s (_fetch_segments): %s', status_code, exc)
            raise VexaConnectionError(str(exc)) from exc
