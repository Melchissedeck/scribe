# Scribe

[![CI](https://github.com/Melchissedeck/scribe/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/Melchissedeck/scribe/actions/workflows/ci.yml)

Assistant de réunion intelligent : captation, transcription, compte-rendu et suivi des actions.

## Application en ligne

- Frontend : https://scribefrontend-production-93be.up.railway.app
- Backend : https://scribe-production-a094.up.railway.app (healthcheck sur
  `/health`, documentation interactive sur `/docs`)

## Stack technique

- Backend : FastAPI, PostgreSQL, SQLAlchemy, Alembic (migrations)
- Frontend : HTML, CSS, JavaScript (sans framework, sans étape de build)
- Authentification : JWT (python-jose), mots de passe hashés avec bcrypt
- Captation visio : bot de réunion Vexa (Google Meet, Teams, Zoom)
- Captation dictaphone : micro du navigateur (API MediaRecorder)
- Transcription : Whisper via l'API Groq (dictaphone), transcript diarisé
  Vexa (visio)
- Diarisation dictaphone : pyannote.audio, exécuté en interne sur le backend
- Génération du compte-rendu et classification : Claude Sonnet via l'API
  Anthropic, en sortie structurée
- Export : PDF et Word
- Supervision : Sentry (optionnel), journal d'audit interne

## Fonctionnalités

- Inscription, connexion, gestion de compte, écran de consentement RGPD
- Captation d'une réunion en visio (bot Vexa) ou au dictaphone (micro)
- Transcription automatique, avec attribution des propos par locuteur
- Compte-rendu structuré (décisions, actions, responsables, échéances) et
  classification par segment (ton, thème, urgence)
- Tableau de bord avec historique, filtres (date, thème, statut) et export
  des comptes-rendus (PDF, Word)
- Anonymisation des transcriptions et suppression de compte (droit à
  l'effacement RGPD)

## Installation

### Prérequis

- [Docker](https://www.docker.com/) et Docker Compose (pour la base de
  données PostgreSQL locale)
- Python 3.12 ou supérieur
- [mkcert](https://github.com/FiloSottile/mkcert) (certificat HTTPS local
  pour le frontend)
- Des clés API valides pour Vexa, Anthropic, Groq et Pyannote si vous
  voulez tester la captation et la transcription (voir la section
  [Variables d'environnement](#variables-denvironnement) ci-dessous ; sans
  elles, l'authentification et le tableau de bord fonctionnent quand même)

### Backend

```bash
# 1. Cloner le dépôt
git clone https://github.com/Melchissedeck/scribe.git
cd scribe

# 2. Démarrer PostgreSQL en local via Docker
docker-compose up -d db

# 3. Créer et activer un environnement virtuel
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Configurer les variables d'environnement
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
# Puis éditer .env et renseigner vos propres clés API

# 6. Appliquer les migrations de base de données
alembic upgrade head

# 7. Lancer le serveur de développement
uvicorn app.main:app --reload
```

L'API est alors disponible sur `http://127.0.0.1:8000`, avec une
documentation interactive sur `http://127.0.0.1:8000/docs`.

Alternative : `docker-compose up` (sans `-d db`) construit et lance
également le service `api` en conteneur, sans environnement virtuel local.

### Frontend

Le frontend est servi en HTTPS local via un petit serveur Python
(`frontend/serve.py`), car certaines API navigateur utilisées (micro,
`MediaRecorder`) exigent un contexte sécurisé.

```bash
# 1. Générer un certificat local de confiance, une seule fois
cd frontend
mkcert -install
mkcert -cert-file cert.pem -key-file key.pem localhost 127.0.0.1

# 2. Lancer le serveur
python serve.py
```

Le frontend est alors disponible sur `https://127.0.0.1:5500`.
`frontend/js/api.js` détecte automatiquement s'il tourne en local ou sur
Railway et bascule vers la bonne URL d'API ; aucune configuration
supplémentaire n'est nécessaire côté frontend.

Vérifiez que `ALLOWED_ORIGIN` dans `backend/.env` correspond exactement à
cette adresse (`https://127.0.0.1:5500`), sinon les requêtes échouent avec
une erreur CORS visible dans la console du navigateur (F12).

### Variables d'environnement

Définies dans `backend/.env` (jamais commité), à partir du modèle
`backend/.env.example` :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (`localhost:5433` avec le Docker Compose fourni) |
| `JWT_SECRET_KEY` | Clé de signature des tokens JWT |
| `ALLOWED_ORIGIN` | Origine autorisée par CORS (URL du frontend) |
| `VEXA_API_KEY` | Clé de l'API Vexa (captation visio) |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Clé et modèle pour la génération du compte-rendu (Claude Sonnet) |
| `GROQ_API_KEY` | Clé de l'API Groq (transcription Whisper, mode dictaphone) |
| `PYANNOTE_AUTH_TOKEN` | Jeton Hugging Face pour le modèle de diarisation pyannote |
| `FFMPEG_BIN` | Chemin vers l'exécutable ffmpeg, si non présent dans le `PATH` |
| `TORCH_NUM_THREADS` | Nombre de threads PyTorch pour l'inférence pyannote (défaut : 1) |
| `ADMIN_API_KEY` | Clé protégeant les routes internes (`GET /admin/logs`) |
| `SENTRY_DSN` | Supervision des erreurs (optionnelle, vide = désactivée) |

## Qualité de code (backend)

Depuis `backend/`, avec l'environnement virtuel activé :

```bash
python -m ruff check .
python -m mypy .
python -m pytest
```

La configuration se trouve dans `backend/pyproject.toml` (ruff, mypy) et
`backend/pytest.ini` (pytest, couverture).

Ces trois commandes s'exécutent automatiquement sur chaque pull request
vers `dev` ou `main`, ainsi que sur chaque push vers ces deux branches, via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Déploiement

L'application tourne en ligne sur Railway (voir les liens en tête de ce
document), déployée automatiquement depuis `main`. Trois services Railway
dans le même projet :

1. **PostgreSQL** (plugin managé).
2. **Backend**, *Root Directory* `backend/`, build via `backend/Dockerfile`.
   Les migrations Alembic s'appliquent automatiquement à chaque démarrage du
   conteneur. Variables d'environnement : `DATABASE_URL` (référence vers le
   plugin Postgres), `JWT_SECRET_KEY`, `ALLOWED_ORIGIN` (URL du frontend),
   `VEXA_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `GROQ_API_KEY`,
   `PYANNOTE_AUTH_TOKEN`, `ADMIN_API_KEY`, `SENTRY_DSN` (optionnelle).
3. **Frontend**, *Root Directory* `frontend/`, build via
   `frontend/Dockerfile`. `frontend/js/api.js` bascule automatiquement entre
   l'API locale et l'API déployée selon le nom d'hôte.

Chaque service a **"Wait for CI to pass"** activé (Settings → Source) : un
déploiement ne part que si `.github/workflows/ci.yml` est passé au vert sur
le commit poussé sur `main`, ce qui répond à l'exigence "déploiement
automatique après succès des tests". Le pipeline pyannote (torch) n'est
chargé qu'à la première diarisation dictaphone, pas au démarrage, pour
limiter l'empreinte mémoire.

## Structure du projet

```
scribe/
├── backend/
│   ├── app/
│   │   ├── models/      -> modèles SQLAlchemy
│   │   ├── routes/      -> routes FastAPI, un fichier par domaine
│   │   ├── schemas/     -> schémas Pydantic (validation entrée/sortie)
│   │   ├── services/    -> logique métier (Vexa, Whisper, pyannote, LLM...)
│   │   ├── config.py    -> configuration centralisée
│   │   ├── database.py  -> connexion SQLAlchemy, session, Base
│   │   ├── dependencies.py -> dépendances FastAPI réutilisables
│   │   └── main.py      -> point d'entrée FastAPI
│   ├── alembic/          -> migrations de base de données
│   ├── tests/             -> tests pytest
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── css/               -> feuilles de style (tokens.css = charte)
│   ├── js/                 -> modules JS, un par écran + api.js commun
│   ├── pages/               -> fichiers HTML, un par écran
│   ├── certs/                -> certificats HTTPS locaux (jamais commités)
│   └── serve.py              -> serveur HTTPS local pour tester le frontend
├── docs/                      -> documentation technique du projet
├── docker-compose.yml
└── README.md
```

## Documentation complémentaire

Le dossier [`docs/`](docs/) contient la documentation technique détaillée :
modèle de données, stratégie de tests, schéma du compte-rendu structuré,
journal d'audit, tests de charge, ainsi que les livrables académiques du
projet (dossier de cadrage, spécifications et architecture, rapport
technique).
