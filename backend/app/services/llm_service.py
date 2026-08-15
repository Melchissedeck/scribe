import logging

from together import Together
from together.error import TogetherException

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service responsable de la génération de résumés via l'API TogetherAI."""

    def __init__(self):
        self.client = Together(api_key=settings.together_api_key)
        self.model = settings.together_model

    def generate_summary(self, transcription: str) -> str | None:
        """
        Génère un résumé en texte libre à partir d'une transcription.

        Retourne None (au lieu de lever une exception) en cas d'erreur
        API (timeout, quota dépassé, réseau, etc.) afin de ne jamais
        faire planter l'application appelante.
        """
        if not transcription or not transcription.strip():
            logger.warning("generate_summary appelé avec une transcription vide.")
            return None

        prompt = (
            "Voici la transcription d'un enregistrement audio. "
            "Rédige un résumé clair et concis en texte libre, "
            "en français, qui reprend les points essentiels.\n\n"
            f"Transcription :\n{transcription}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content

        except TogetherException as exc:
            logger.error("Erreur TogetherAI lors de la génération du résumé: %s", exc)
            return None

        except Exception as exc:
            logger.error("Erreur inattendue lors de l'appel LLM: %s", exc)
            return None