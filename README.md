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

## Déploiement

L'application tourne en ligne sur Railway, déployée automatiquement depuis
`dev` :

- Backend : https://scribe-production-a094.up.railway.app (healthcheck sur
  `/health`, documentation interactive sur `/docs`)
- Frontend : https://scribefrontend-production-93be.up.railway.app

Trois services Railway dans le même projet :

1. **PostgreSQL** (plugin managé).
2. **Backend** — *Root Directory* `backend/`, build via `backend/Dockerfile`.
   Les migrations Alembic s'appliquent automatiquement à chaque démarrage du
   conteneur. Variables d'environnement : `DATABASE_URL` (référence vers le
   plugin Postgres), `JWT_SECRET_KEY`, `ALLOWED_ORIGIN` (URL du frontend),
   `VEXA_API_KEY`, `TOGETHER_API_KEY`, `TOGETHER_MODEL`, `GROQ_API_KEY`,
   `PYANNOTE_AUTH_TOKEN`, `ADMIN_API_KEY`, `SENTRY_DSN` (optionnelle).
3. **Frontend** — *Root Directory* `frontend/`, build via
   `frontend/Dockerfile`. `frontend/js/api.js` bascule automatiquement entre
   l'API locale et l'API déployée selon le nom d'hôte.

Chaque service a **"Wait for CI to pass"** activé (Settings → Source) : un
déploiement ne part que si `.github/workflows/ci.yml` est passé au vert sur
le commit poussé, ce qui répond à l'exigence "déploiement automatique après
succès des tests" sans dépendre de la branche `main` (volontairement vide
jusqu'à la toute fin du projet — voir `CLAUDE.md`). Le pipeline pyannote
(torch) n'est chargé qu'à la première diarisation dictaphone, pas au
démarrage, pour limiter l'empreinte mémoire.

Quand `main` recevra le merge final, le plus simple sera de répéter la
même configuration (nouveau service ou branche source changée) plutôt que
de reconfigurer quoi que ce soit d'existant.

## Structure du projet

- `backend/` : API FastAPI
- `frontend/` : interface utilisateur
- `docs/` : documentation technique (architecture, base de données, charte)
