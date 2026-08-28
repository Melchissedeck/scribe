import logging

import anthropic

from app.config import settings
from app.exceptions import LLMError
from app.schemas.llm_summary import SegmentClassificationResult, StructuredSummary

logger = logging.getLogger(__name__)

MAX_TOKENS = 16000

# Timeout explicite par appel : couvre la latence réseau + génération.
# Plus généreux que la valeur par défaut du SDK (10 min) n'est pas
# nécessaire, mais on la borne pour ne jamais laisser une requête HTTP
# de l'app pendre indéfiniment sur un appel LLM.
LLM_TIMEOUT_SECONDS = 90.0


class LLMService:
    """Service responsable de la génération de résumés via l'API Anthropic."""

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        self.model = settings.anthropic_model

    def _handle_api_error(self, exc: Exception, context: str) -> LLMError:
        """
        Traduit une exception du SDK Anthropic en LLMError typée, en
        loguant systématiquement le type d'erreur pour le suivi de la
        consommation et des incidents.
        """
        if isinstance(exc, anthropic.APITimeoutError):
            logger.error("[LLM][timeout] %s: %s", context, exc)
            return LLMError(
                error_type="timeout",
                message="Le service IA met trop de temps à répondre. Veuillez réessayer dans quelques instants.",
            )

        if isinstance(exc, anthropic.RateLimitError):
            logger.error("[LLM][quota_exceeded] %s: %s", context, exc)
            return LLMError(
                error_type="quota_exceeded",
                message="Le quota de l'API IA a été atteint. Veuillez réessayer un peu plus tard.",
            )

        if isinstance(exc, anthropic.APIStatusError):
            logger.error("[LLM][api_error] %s: %s", context, exc)
            return LLMError(
                error_type="api_error",
                message="Le service IA est momentanément indisponible. Veuillez réessayer dans quelques instants.",
            )

        if isinstance(exc, anthropic.APIConnectionError):
            logger.error("[LLM][connection] %s: %s", context, exc)
            return LLMError(
                error_type="connection",
                message="Impossible de contacter le service IA. Veuillez réessayer dans quelques instants.",
            )

        logger.error("[LLM][invalid_response] %s: %s", context, exc)
        return LLMError(
            error_type="invalid_response",
            message="Le service IA a renvoyé une réponse inattendue. Veuillez réessayer.",
        )

    def generate_summary(self, transcription: str) -> str | None:
        """
        Génère un résumé en texte libre à partir d'une transcription.

        Retourne None uniquement si la transcription est vide (rien à
        faire). En cas d'échec de l'appel API (timeout, quota dépassé,
        réponse invalide, etc.), lève LLMError plutôt que de faire
        planter l'application appelante.
        """
        if not transcription or not transcription.strip():
            logger.warning("generate_summary appelé avec une transcription vide.")
            return None

        prompt = (
            "Rédige un résumé clair et concis, en français, de cette "
            f"transcription de réunion.\n\nTranscription :\n{transcription}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return next((block.text for block in response.content if block.type == "text"), None)

        except Exception as exc:
            raise self._handle_api_error(exc, "génération du résumé") from exc

    def generate_structured_summary(self, transcription: str) -> StructuredSummary | None:
        """
        Génère un compte-rendu structuré (thèmes, décisions, actions) à
        partir d'une transcription. La conformité du JSON au schéma
        StructuredSummary est garantie côté API (structured outputs).

        Retourne None uniquement si la transcription est vide. Lève
        LLMError si l'appel API échoue.
        """
        if not transcription or not transcription.strip():
            logger.warning("generate_structured_summary appelé avec une transcription vide.")
            return None

        # Le schéma StructuredSummary (voir output_format ci-dessous) porte
        # déjà les descriptions de chaque champ envoyées au modèle : pas
        # besoin de les redire ici en prose, juste le comportement que le
        # schéma ne couvre pas (langue, ne pas halluciner).
        system_prompt = (
            "Analyse cette transcription de réunion selon le schéma "
            "demandé. N'invente rien : liste vide ou null si une "
            "information est absente."
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

        except Exception as exc:
            raise self._handle_api_error(exc, "génération du compte-rendu structuré") from exc

    def classify_segments(self, segments: list[str]) -> SegmentClassificationResult | None:
        """
        Classifie chaque segment d'une transcription selon son ton, son
        thème et son urgence (analyse plus fine que la classification
        globale de generate_structured_summary).

        `segments` est la liste des textes de segments dans leur ordre
        chronologique ; le LLM doit renvoyer une classification par index
        de segment (0-based), à faire correspondre par l'appelant.

        Retourne None uniquement si la liste est vide. Lève LLMError si
        l'appel API échoue.
        """
        if not segments:
            logger.warning("classify_segments appelé avec une liste de segments vide.")
            return None

        system_prompt = (
            "Classe chaque segment numéroté ci-dessous selon le schéma "
            "demandé, dans le même ordre, en conservant son index exact."
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

        except Exception as exc:
            raise self._handle_api_error(exc, "classification des segments") from exc
