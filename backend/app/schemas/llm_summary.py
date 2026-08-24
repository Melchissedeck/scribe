from typing import Optional

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """Une action décidée pendant la réunion."""

    description: str = Field(..., description="Ce qui doit être fait")
    responsable: Optional[str] = Field(
        default=None, description="Personne en charge de l'action, si mentionnée"
    )
    echeance: Optional[str] = Field(
        default=None, description="Échéance de l'action, si mentionnée (texte libre ou date)"
    )


class StructuredSummary(BaseModel):
    """Compte-rendu structuré généré par le LLM à partir d'une transcription."""

    themes: list[str] = Field(
        default_factory=list, description="Sujets principaux abordés pendant la réunion"
    )
    decisions: list[str] = Field(
        default_factory=list, description="Décisions prises pendant la réunion"
    )
    actions: list[ActionItem] = Field(
        default_factory=list, description="Actions à réaliser suite à la réunion"
    )
    