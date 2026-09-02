import logging
import time

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import settings
from app.exceptions import VexaConnectionError, VexaInvalidMeetingError

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # secondes
_MAX_RETRIES = 3
_RETRY_DELAYS = (1, 2, 4)  # backoff exponentiel en secondes


def _http_call_with_retry(fn):
    """Execute fn(), retrying on transient network errors or HTTP 429 with exponential backoff.

    Retries on ConnectionError/Timeout and on a 429 (quota dépassé) response — other
    HTTPError statuses (4xx/5xx) are permanent and left to the caller's raise_for_status().
    Raises the last ConnectionError/Timeout, or returns the final 429 response, if all
    retries fail.
    """
    last_exc: Exception | None = None
    response = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = fn()
        except (ConnectionError, Timeout) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_DELAYS[attempt]
                logger.warning(
                    'Vexa - tentative %d/%d échouée, nouvel essai dans %ds: %s',
                    attempt + 1, _MAX_RETRIES, delay, exc,
                )
                time.sleep(delay)
            continue

        if response.status_code == 429 and attempt < _MAX_RETRIES - 1:
            delay = _RETRY_DELAYS[attempt]
            logger.warning(
                'Vexa - quota dépassé (429), tentative %d/%d, nouvel essai dans %ds',
                attempt + 1, _MAX_RETRIES, delay,
            )
            time.sleep(delay)
            continue

        return response

    if response is not None:
        return response
    raise last_exc  # type: ignore[misc]


class VexaAgent:
    """Client HTTP pour l'API Vexa — envoie le bot et récupère les transcriptions."""

    def __init__(self):
        self.base_url = 'https://api.cloud.vexa.ai'
        self.headers = {
            'X-API-Key': settings.vexa_api_key,
            'Content-Type': 'application/json',
        }

    def send_bot(self, platform: str, meeting_id: str, bot_name: str = 'Scribe', meeting_url: str | None = None) -> dict:
        """Envoie le bot Vexa dans une réunion.

        Args:
            platform: Plateforme de visioconférence (ex. 'google_meet', 'teams').
            meeting_id: Identifiant natif de la réunion sur la plateforme.
            bot_name: Nom affiché par le bot dans la réunion.
            meeting_url: URL directe de la réunion (prioritaire sur platform + meeting_id).

        Returns:
            La réponse JSON de l'API Vexa confirmant l'envoi du bot.

        Raises:
            VexaInvalidMeetingError: Si le lien de réunion est invalide (HTTP 422).
            VexaConnectionError: Si l'API est inaccessible ou renvoie une erreur HTTP.
        """
        if meeting_url:
            payload: dict = {'meeting_url': meeting_url, 'bot_name': bot_name}
        else:
            payload = {'platform': platform, 'native_meeting_id': meeting_id, 'bot_name': bot_name}
        try:
            response = _http_call_with_retry(
                lambda: requests.post(f'{self.base_url}/bots', headers=self.headers, json=payload, timeout=_TIMEOUT)
            )
            response.raise_for_status()
            return response.json()
        except (ConnectionError, Timeout) as exc:
            logger.error('Vexa - erreur de connexion (send_bot): %s', exc)
            raise VexaConnectionError() from exc
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            logger.error('Vexa - erreur HTTP %s (send_bot): %s', status_code, exc)
            if status_code == 422:
                raise VexaInvalidMeetingError() from exc
            raise VexaConnectionError() from exc

    def stop_bot(self, platform: str, meeting_id: str) -> int:
        """Retire le bot Vexa d'une réunion en cours.

        Args:
            platform: Plateforme de visioconférence.
            meeting_id: Identifiant natif de la réunion.

        Returns:
            Le code HTTP retourné par l'API Vexa (typiquement 200).

        Raises:
            VexaConnectionError: Si l'API est inaccessible ou renvoie une erreur HTTP.
        """
        try:
            response = _http_call_with_retry(
                lambda: requests.delete(
                    f'{self.base_url}/bots/{platform}/{meeting_id}', headers=self.headers, timeout=_TIMEOUT
                )
            )
            return response.status_code
        except (ConnectionError, Timeout) as exc:
            logger.error('Vexa - erreur de connexion (stop_bot): %s', exc)
            raise VexaConnectionError() from exc
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 'inconnu'
            logger.error('Vexa - erreur HTTP %s (stop_bot): %s', status_code, exc)
            raise VexaConnectionError() from exc

    def get_transcript(self, platform: str, meeting_id: str) -> str:
        """Retourne la transcription formatée sous forme de texte brut.

        Chaque segment est rendu sur une ligne au format « Locuteur : texte ».
        Les segments sans contenu textuel sont ignorés.

        Args:
            platform: Plateforme de visioconférence.
            meeting_id: Identifiant natif de la réunion.

        Returns:
            Transcription complète, une ligne par segment, séparées par \\n.

        Raises:
            VexaConnectionError: Si l'API est inaccessible ou renvoie une erreur HTTP.
        """
        segments = self._fetch_segments(platform, meeting_id)
        lines = []
        for seg in segments:
            speaker = seg.get('speaker', 'Inconnu')
            text = seg.get('text', '').strip()
            if text:
                lines.append(f'{speaker} : {text}')
        return '\n'.join(lines)

    def get_diarized_segments(self, platform: str, meeting_id: str) -> list[dict]:
        """Retourne les segments diarisés bruts de la réunion.

        Args:
            platform: Plateforme de visioconférence.
            meeting_id: Identifiant natif de la réunion.

        Returns:
            Liste de segments, chacun contenant speaker, text, start et end (secondes).

        Raises:
            VexaConnectionError: Si l'API est inaccessible ou renvoie une erreur HTTP.
        """
        return self._fetch_segments(platform, meeting_id)

    def _fetch_segments(self, platform: str, meeting_id: str) -> list[dict]:
        """Appelle l'API Vexa et retourne la liste brute des segments.

        Args:
            platform: Plateforme de visioconférence.
            meeting_id: Identifiant natif de la réunion.

        Returns:
            Liste des segments retournés par l'API, vide si la clé 'segments' est absente.

        Raises:
            VexaConnectionError: Si l'API est inaccessible ou renvoie une erreur HTTP.
        """
        try:
            response = _http_call_with_retry(
                lambda: requests.get(
                    f'{self.base_url}/transcripts/{platform}/{meeting_id}', headers=self.headers, timeout=_TIMEOUT
                )
            )
            response.raise_for_status()
            return response.json().get('segments', [])
        except (ConnectionError, Timeout) as exc:
            logger.error('Vexa - erreur de connexion (_fetch_segments): %s', exc)
            raise VexaConnectionError() from exc
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 'inconnu'
            logger.error('Vexa - erreur HTTP %s (_fetch_segments): %s', status_code, exc)
            raise VexaConnectionError() from exc
