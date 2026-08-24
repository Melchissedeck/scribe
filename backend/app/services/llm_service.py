import json
import logging
import re

from pydantic import ValidationError
from together import Together
from together.error import TogetherException

from app.config import settings
from app.schemas.llm_summary import StructuredSummary

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
            message = response.choices[0].message
            return message.content if message is not None else None

        except TogetherException as exc:
            logger.error("Erreur TogetherAI lors de la génération du résumé: %s", exc)
            return None

        except Exception as exc:
            logger.error("Erreur inattendue lors de l'appel LLM: %s", exc)
            return None

    def generate_structured_summary(
        self, transcription: str, max_attempts: int = 2
    ) -> StructuredSummary | None:
        """
        Génère un compte-rendu structuré (thèmes, décisions, actions) en
        JSON à partir d'une transcription.

        Retourne None si la transcription est vide, si l'API échoue, ou
        si le LLM ne parvient pas à produire un JSON valide après
        `max_attempts` tentatives. Ne lève jamais d'exception.
        """
        if not transcription or not transcription.strip():
            logger.warning("generate_structured_summary appelé avec une transcription vide.")
            return None

        system_prompt = (
            "Tu es un assistant qui génère des comptes-rendus de réunion. "
            "Tu dois répondre UNIQUEMENT avec un objet JSON valide, sans "
            "aucun texte avant ou après, sans balises markdown, respectant "
            "strictement ce schéma :\n"
            "{\n"
            '  "themes": ["string", ...],\n'
            '  "decisions": ["string", ...],\n'
            '  "actions": [\n'
            "    {\n"
            '      "description": "string",\n'
            '      "responsable": "string ou null",\n'
            '      "echeance": "string ou null"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Si une information n'est pas mentionnée dans la transcription, "
            "utilise une liste vide ou null. N'invente jamais d'information."
        )

        user_prompt = f"Transcription de la réunion :\n{transcription}"

        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                message = response.choices[0].message
                raw_content = message.content if message is not None else None

            except TogetherException as exc:
                logger.error("Erreur TogetherAI lors de la génération du compte-rendu structuré: %s", exc)
                return None

            except Exception as exc:
                logger.error("Erreur inattendue lors de l'appel LLM structuré: %s", exc)
                return None

            parsed = self._parse_structured_response(raw_content)
            if parsed is not None:
                return parsed

            logger.warning(
                "Tentative %d/%d : JSON invalide ou non conforme retourné par le LLM.",
                attempt, max_attempts,
            )

        logger.error("Échec de la génération d'un JSON valide après %d tentatives.", max_attempts)
        return None

    @staticmethod
    def _parse_structured_response(raw_content: str | None) -> StructuredSummary | None:
        """
        Extrait et valide un StructuredSummary à partir de la réponse brute
        du LLM. Retourne None si le contenu n'est pas un JSON valide et
        conforme au schéma.
        """
        if not raw_content:
            return None

        # Certains modèles enveloppent parfois leur JSON dans des balises
        # markdown (```json ... ```) malgré la consigne : on les retire.
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content.strip())

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("JSON mal formé retourné par le LLM: %s", exc)
            return None

        try:
            return StructuredSummary.model_validate(data)
        except ValidationError as exc:
            logger.warning("JSON ne respecte pas le schéma attendu: %s", exc)
            return None