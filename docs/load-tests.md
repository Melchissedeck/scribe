# Tests de charge

Ce document regroupe les tests de charge réalisés sur le projet : réunions
visio simultanées (US-67) et traitement audio dictaphone (US-70).

---

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

---

# Tests de charge — Traitement audio dictaphone (US-70)

## Objectif

Vérifier la robustesse du pipeline de traitement audio dictaphone (upload,
découpage, transcription Whisper, lancement de la diarisation Pyannote) sous
plusieurs fichiers traités en parallèle, contre l'API de production.

## Script

**Fichier :** `backend/tests/test_load_audio.py`  
**Dépendances :** `httpx` (déjà dans `requirements.txt`), `asyncio`/`wave` (stdlib)

Génère lui-même un fichier WAV mono synthétique de la durée demandée (sans
dépendance à ffmpeg), pour rester exécutable sur n'importe quelle machine.

### Configuration

| Variable d'environnement | Description | Défaut |
|---|---|---|
| `LOAD_TEST_BASE_URL` | URL de l'API cible | URL production Railway |
| `LOAD_TEST_USER1_EMAIL` / `_PASSWORD` | Compte de test | — |
| `LOAD_TEST_AUDIO_N_FILES` | Nombre de fichiers traités en parallèle | `3` |
| `LOAD_TEST_AUDIO_DURATION_S` | Durée de chaque fichier de test (secondes) | `60` |
| `LOAD_TEST_AUDIO_WAIT_DIARIZE` | `1` = attend la fin complète de la diarisation | `0` |

### Flux simulé par fichier

1. `POST /meetings` → création de l'enregistrement
2. `POST /meetings/{id}/upload-audio` → upload du fichier
3. `POST /meetings/{id}/transcribe` → découpage (si > 8 min) + transcription Whisper
4. `POST /meetings/{id}/diarize` → lancement de la diarisation (tâche de fond, réponse immédiate depuis l'architecture asynchrone mise en place pendant le sprint)
5. *(optionnel, `LOAD_TEST_AUDIO_WAIT_DIARIZE=1`)* Polling de `GET /meetings/{id}/diarize-status` jusqu'à complétion

### Exécution

```bash
LOAD_TEST_USER1_EMAIL=user@example.com \
LOAD_TEST_USER1_PASSWORD=motdepasse \
LOAD_TEST_AUDIO_N_FILES=3 \
LOAD_TEST_AUDIO_DURATION_S=60 \
python backend/tests/test_load_audio.py
```

---

## Résultats

### Scénario 1 — 3 fichiers de 30s en parallèle (2026-08-28)

| Métrique | /upload-audio | /transcribe | /diarize (lancement) |
|---|---|---|---|
| Moyenne | 417 ms | 611 ms | 176 ms |
| P50 | 430 ms | 539 ms | 180 ms |
| Max | 460 ms | 807 ms | 182 ms |

- Fichiers réussis : 3/3 — Taux d'échec : 0 % — Durée totale : 1,6 s

### Scénario 2 — 2 fichiers de 10 min en parallèle (2026-08-28)

Ce scénario dépasse le seuil de découpage (8 min), donc chaque fichier est
réellement fragmenté en 2 tranches et transcrit via 2 appels Whisper
distincts — exerce le chemin de découpage visé par ce ticket, pas seulement
un fichier court en un seul appel.

| Métrique | /upload-audio | /transcribe | /diarize (lancement) |
|---|---|---|---|
| Moyenne | 6 222 ms | 2 270 ms | 173 ms |
| Max | 6 283 ms | 2 296 ms | 174 ms |

- Fichiers réussis : 2/2 — Taux d'échec : 0 % — Durée totale : 9,3 s

**Observation :** `/diarize` répond en ~175 ms quel que soit le nombre de
fichiers ou leur durée — confirme que le passage en tâche de fond (voir plus
bas) découple bien le temps de réponse HTTP du temps de traitement réel.

### Consommation mémoire et CPU sous charge

Le script ci-dessus ne peut pas mesurer la consommation mémoire du serveur
(aucune route d'introspection exposée) : ces données viennent de l'onglet
**Metrics** de Railway, relevées pendant un traitement réel (diarisation
d'un enregistrement de 11 minutes de parole, seul sur le conteneur) :

- **CPU** : plafonne à ~1,2–1,3 vCPU (quota du conteneur), en dents de scie
  régulières correspondant au traitement par fenêtres glissantes de
  Pyannote (segmentation puis embedding). Pas de pic anormal.
- **Mémoire** : oscille entre ~1 Go et ~2,3 Go pendant le traitement, sans
  dérive continue (pas de fuite mémoire observée sur la durée du test).
- **Temps de réponse des autres routes** : reste sous 35 ms (p99) pendant
  tout le traitement — confirme que la diarisation en tâche de fond
  n'affame pas le reste de l'API.

## Goulots d'étranglement identifiés

### 1. CPU disponible pour Pyannote (principal)

**Impact :** Élevé  
**Symptôme :** Avec ~1,2 vCPU alloué, diariser un enregistrement réel de 11
minutes de parole peut prendre 20 à 25 minutes (mesuré en conditions
réelles, hors ce script de charge). Plusieurs diarisations concurrentes se
partageraient ce même quota CPU et ralentiraient proportionnellement.  
**Piste :** Augmenter les ressources CPU allouées au service Railway, ou
limiter le nombre de diarisations traitées en parallèle (file d'attente)
plutôt que de les lancer toutes en tâche de fond sans limite.

### 2. Upload réseau sur fichiers longs

**Impact :** Moyen  
**Symptôme :** L'upload d'un fichier de 10 min (~21 Mo en WAV non compressé,
tel que produit par ce script de test) prend ~6 s ; en pratique un vrai
enregistrement WebM/Opus du navigateur est bien plus compact (quelques Mo),
donc ce chiffre est un majorant plutôt qu'une mesure réaliste.  
**Piste :** Aucune action nécessaire à ce stade — à surveiller si le format
d'enregistrement change.

### 3. Fichiers orphelins en cas de redéploiement pendant un traitement

**Impact :** Moyen  
**Symptôme :** `run_diarization` tourne dans une tâche de fond sans
persistance de file d'attente : un redéploiement Railway pendant un
traitement en cours tue le conteneur, et le `recording.diarization_status`
reste bloqué à `"processing"` indéfiniment (observé pendant le
développement de ce sprint).  
**Piste :** Ajouter un job de nettoyage périodique qui repasse en `"failed"`
les enregistrements `"processing"` depuis plus d'une durée seuil (ex. 1h).
