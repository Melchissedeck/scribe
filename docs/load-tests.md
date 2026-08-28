# Tests de charge — Réunions visio simultanées

## Objectif

Vérifier la robustesse de l'intégration Vexa et de la base de données PostgreSQL sous charge, en simulant plusieurs démarrages de réunion visio en parallèle.

## Script

**Fichier :** `backend/tests/test_load_visio.py`  
**Dépendances :** `httpx` (déjà dans `requirements.txt`), `asyncio` (stdlib)

### Configuration

| Variable d'environnement | Description | Défaut |
|--------------------------|-------------|--------|
| `LOAD_TEST_BASE_URL` | URL de l'API cible | URL production Railway |
| `LOAD_TEST_USER1_EMAIL` | Email compte de test n°1 | — |
| `LOAD_TEST_USER1_PASSWORD` | Mot de passe compte n°1 | — |
| `LOAD_TEST_USER2_EMAIL` | Email compte de test n°2 (optionnel) | — |
| `LOAD_TEST_USER2_PASSWORD` | Mot de passe compte n°2 (optionnel) | — |
| `LOAD_TEST_N_SESSIONS` | Nombre de sessions simultanées | `5` |
| `LOAD_TEST_PLATFORM` | Plateforme (`google_meet`, `zoom`, `teams`) | `google_meet` |
| `LOAD_TEST_MEETING_ID` | ID de réunion | `abc-defg-hij` |
| `LOAD_TEST_MEETING_URL` | URL complète (prioritaire sur MEETING_ID) | — |

### Exécution

```bash
# Exemple avec 10 sessions simultanées
LOAD_TEST_USER1_EMAIL=user1@example.com \
LOAD_TEST_USER1_PASSWORD=motdepasse1 \
LOAD_TEST_USER2_EMAIL=user2@example.com \
LOAD_TEST_USER2_PASSWORD=motdepasse2 \
LOAD_TEST_N_SESSIONS=10 \
python backend/tests/test_load_visio.py
```

### Flux simulé par session

1. `POST /auth/login` → obtention du token JWT
2. `POST /recording/start` → envoi du bot Vexa dans la réunion
3. Attente de 5 secondes (simulation d'une réunion courte)
4. `POST /recording/{id}/stop` → arrêt du bot et récupération de la transcription

---

## Résultats

> *À compléter après exécution du script.*

### Scénario 1 — 2 sessions simultanées (2026-08-28)

2 comptes Google Meet distincts, chacun avec son propre lien de réunion, lancés en parallèle.

| Métrique | /auth/login | /recording/start | /recording/stop |
|----------|-------------|------------------|-----------------|
| Moyenne  | 620 ms      | 1 153 ms         | 683 ms          |
| P50      | 648 ms      | 1 180 ms         | 908 ms          |
| P95      | 648 ms      | 1 180 ms         | 908 ms          |
| P99      | 648 ms      | 1 180 ms         | 908 ms          |
| Max      | 648 ms      | 1 180 ms         | 908 ms          |

- Sessions réussies : 2/2
- Taux d'échec : 0 %
- Durée totale (incluant 5s d'attente simulée) : 7,8 s

**Observation :** Le bot Vexa répond en ~1,1 s pour envoyer la confirmation de démarrage.
Le temps réel de join côté Google Meet reste de 15–30 s (traitement asynchrone côté Vexa).

### Scénario 2 — 10 sessions simultanées

*(à réaliser avec comptes supplémentaires)*

### Scénario 3 — 20 sessions simultanées

*(à réaliser avec comptes supplémentaires)*

---

## Goulots d'étranglement identifiés

### 1. API Vexa (principal)

**Impact :** Élevé  
**Symptôme :** `POST /recording/start` prend 15–30s car Vexa doit spawner un bot, naviguer vers l'URL et rejoindre la réunion.  
**Piste :** Contacter Vexa pour activer un pool de bots préchauffés (option payante). Sans ça, les requêtes simultanées s'accumulent côté Vexa.

### 2. Pool de connexions PostgreSQL

**Impact :** Moyen  
**Symptôme :** Avec > 20 sessions simultanées, SQLAlchemy peut saturer son pool de connexions par défaut (5 connexions).  
**Piste :** Augmenter `pool_size` et `max_overflow` dans `database.py` :
```python
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
```

### 3. Retry VexaAgent (aggravant)

**Impact :** Moyen  
**Symptôme :** En cas d'erreur réseau, le retry avec backoff exponentiel (1s + 2s + 4s) bloque le thread pendant 7s par session.  
**Piste :** Passer `vexa_agent.py` en `asyncio`/`httpx` pour libérer le thread pendant les retries.

### 4. Timeout HTTP (10s)

**Impact :** Faible  
**Symptôme :** Le timeout de 10s dans `vexa_agent.py` est inférieur au temps de join réel de Vexa (15–30s), ce qui génère des faux TimeoutError.  
**Piste :** Augmenter `_TIMEOUT` à 45s dans `vexa_agent.py`.
