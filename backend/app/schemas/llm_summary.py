
from typing import Literal

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """Une action décidée pendant la réunion."""

    description: str = Field(..., description="Ce qui doit être fait")
    responsable: str | None = Field(
        default=None, description="Personne en charge de l'action, si mentionnée"
    )
    echeance: str | None = Field(
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


class SegmentClassification(BaseModel):
    """Classification d'un segment individuel de la transcription."""

    index: int = Field(
        ..., description="Index du segment dans la transcription (0-based, ordre chronologique)"
    )
    tone: Literal["neutre", "positif", "négatif", "tendu"] = Field(
        ..., description="Ton dominant exprimé dans ce segment"
    )
    theme: str = Field(..., description="Thème ou sujet principal abordé dans ce segment")
    urgency: Literal["faible", "moyenne", "élevée"] = Field(
        ..., description="Niveau d'urgence exprimé dans ce segment"
    )


class SegmentClassificationResult(BaseModel):
    """Classification ton/thème/urgence de chaque segment d'une transcription."""

    classifications: list[SegmentClassification] = Field(default_factory=list)
