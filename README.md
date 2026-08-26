# Scribe

[![CI](https://github.com/Melchissedeck/scribe/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/Melchissedeck/scribe/actions/workflows/ci.yml)

Assistant de réunion intelligent : captation, transcription, compte-rendu et suivi des actions.

## Stack technique

- Backend : FastAPI, PostgreSQL, SQLAlchemy
- Frontend : HTML, CSS, JavaScript (sans framework)
- Transcription : Whisper + pyannote (dictaphone), Vexa (visio)
- Génération de compte-rendu : Qwen3.7-Plus via TogetherAI

## Installation

Instructions à venir une fois l'environnement Docker en place.

## Qualité de code (backend)

Depuis `backend/`, avec l'environnement virtuel activé :

```bash
python -m ruff check .
python -m mypy .
python -m pytest
```

La configuration se trouve dans `backend/pyproject.toml` (ruff, mypy) et
`backend/pytest.ini` (pytest, couverture).

Ces trois commandes s'exécutent automatiquement sur chaque pull request vers
`dev` via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Structure du projet

- `backend/` : API FastAPI
- `frontend/` : interface utilisateur
- `docs/` : documentation technique (architecture, base de données, charte)
