import logging

import anthropic

from app.config import settings
from app.schemas.llm_summary import SegmentClassificationResult, StructuredSummary

logger = logging.getLogger(__name__)

MAX_TOKENS = 16000


class LLMService:
    """Service responsable de la génération de résumés via l'API Anthropic."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

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
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return next((block.text for block in response.content if block.type == "text"), None)

        except anthropic.RateLimitError as exc:
            logger.error("Limite de débit Anthropic atteinte lors de la génération du résumé: %s", exc)
            return None

        except anthropic.APIStatusError as exc:
            logger.error("Erreur Anthropic lors de la génération du résumé: %s", exc)
            return None

        except anthropic.APIConnectionError as exc:
            logger.error("Erreur réseau lors de l'appel à Anthropic: %s", exc)
            return None

        except Exception as exc:
            logger.error("Erreur inattendue lors de l'appel LLM: %s", exc)
            return None

    def generate_structured_summary(self, transcription: str) -> StructuredSummary | None:
        """
        Génère un compte-rendu structuré (thèmes, décisions, actions) à
        partir d'une transcription. La conformité du JSON au schéma
        StructuredSummary est garantie côté API (structured outputs).

        Retourne None si la transcription est vide ou si l'appel échoue.
        Ne lève jamais d'exception.
        """
        if not transcription or not transcription.strip():
            logger.warning("generate_structured_summary appelé avec une transcription vide.")
            return None

        system_prompt = (
            "Tu es un assistant qui génère des comptes-rendus de réunion. "
            "Extrait les thèmes abordés, les décisions prises et les "
            "actions à réaliser. Si une information n'est pas mentionnée "
            "dans la transcription, utilise une liste vide ou null. "
            "N'invente jamais d'information."
        )

        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Transcription de la réunion :\n{transcription}"}],
                output_format=StructuredSummary,
            )
            return response.parsed_output

        except anthropic.RateLimitError as exc:
            logger.error("Limite de débit Anthropic atteinte lors de la génération du compte-rendu structuré: %s", exc)
            return None

        except anthropic.APIStatusError as exc:
            logger.error("Erreur Anthropic lors de la génération du compte-rendu structuré: %s", exc)
            return None

        except anthropic.APIConnectionError as exc:
            logger.error("Erreur réseau lors de l'appel à Anthropic: %s", exc)
            return None

        except Exception as exc:
            logger.error("Erreur inattendue lors de l'appel LLM structuré: %s", exc)
            return None

    def classify_segments(self, segments: list[str]) -> SegmentClassificationResult | None:
        """
        Classifie chaque segment d'une transcription selon son ton, son
        thème et son urgence (analyse plus fine que la classification
        globale de generate_structured_summary).

        `segments` est la liste des textes de segments dans leur ordre
        chronologique ; le LLM doit renvoyer une classification par index
        de segment (0-based), à faire correspondre par l'appelant.

        Retourne None si la liste est vide ou si l'appel échoue. Ne lève
        jamais d'exception.
        """
        if not segments:
            logger.warning("classify_segments appelé avec une liste de segments vide.")
            return None

        system_prompt = (
            "Tu es un assistant qui analyse des transcriptions de réunion. "
            "Pour CHAQUE segment numéroté ci-dessous, détermine son ton "
            "dominant, son thème principal et son niveau d'urgence. "
            "Réponds pour tous les segments, dans le même ordre, en "
            "reprenant l'index exact de chaque segment."
        )

        numbered_segments = "\n".join(f"[{i}] {text}" for i, text in enumerate(segments))

        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Segments de la réunion :\n{numbered_segments}"}],
                output_format=SegmentClassificationResult,
            )
            return response.parsed_output

        except anthropic.RateLimitError as exc:
            logger.error("Limite de débit Anthropic atteinte lors de la classification des segments: %s", exc)
            return None

        except anthropic.APIStatusError as exc:
            logger.error("Erreur Anthropic lors de la classification des segments: %s", exc)
            return None

        except anthropic.APIConnectionError as exc:
            logger.error("Erreur réseau lors de l'appel à Anthropic: %s", exc)
            return None

        except Exception as exc:
            logger.error("Erreur inattendue lors de la classification des segments: %s", exc)
            return None
