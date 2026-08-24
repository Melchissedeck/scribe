# Scribe

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
```

La configuration se trouve dans `backend/pyproject.toml`.

## Déploiement (Railway)

Le projet se déploie comme deux services Railway distincts dans le même
projet, plus une base PostgreSQL managée. `dev` peut être utilisée comme
environnement de démo ; le même service peut être repointé sur `main` (ou un
second service créé) une fois le merge final effectué, sans rien reconfigurer
d'autre.

1. **Créer le projet Railway** et y ajouter un plugin **PostgreSQL**.
2. **Service backend** : "New Service" → "GitHub Repo" → ce dépôt, avec
   *Root Directory* réglé sur `backend/`. Railway détecte le `Dockerfile`
   automatiquement.
   - Variables d'environnement à définir : `DATABASE_URL` (référence la
     variable Postgres de Railway, ex. `${{Postgres.DATABASE_URL}}`),
     `JWT_SECRET_KEY` (une vraie valeur secrète, pas celle de `.env.example`),
     `ALLOWED_ORIGIN` (URL publique du service frontend, à renseigner après
     l'étape 3), `VEXA_API_KEY`, `TOGETHER_API_KEY`, `TOGETHER_MODEL`,
     `GROQ_API_KEY`, `PYANNOTE_AUTH_TOKEN`. `FFMPEG_BIN` n'est pas nécessaire
     (ffmpeg est installé via apt dans l'image, disponible sur le PATH).
   - Réglez le *Healthcheck Path* sur `/health` dans les paramètres du
     service.
   - Les migrations Alembic s'appliquent automatiquement à chaque démarrage
     du conteneur.
3. **Service frontend** : "New Service" → même dépôt, *Root Directory* réglé
   sur `frontend/`. Railway détecte son propre `Dockerfile`.
4. Une fois le backend déployé, copiez son URL publique et remplacez
   `PRODUCTION_API_BASE_URL` dans `frontend/js/api.js`, puis commitez.
5. Une fois le frontend déployé, copiez son URL publique dans la variable
   `ALLOWED_ORIGIN` du service backend (Railway redéploie automatiquement au
   changement d'une variable).

Le pipeline pyannote (torch) n'est chargé qu'à la première diarisation
dictaphone, pas au démarrage (voir
`app/services/pyannote_service.get_pyannote_service`), pour limiter l'usage
mémoire tant qu'il n'est pas utilisé.

## Structure du projet

- `backend/` : API FastAPI
- `frontend/` : interface utilisateur
- `docs/` : documentation technique (architecture, base de données, charte)
