# Stratégie de tests

Ce document liste les fonctions critiques de chaque brique du projet, l'état
actuel de leur couverture par les tests, et un plan pour atteindre l'objectif
de 70% de couverture sur ces fonctions critiques (US-47, Sprint 3).

La couverture est mesurée avec `pytest-cov`, configuré par défaut dans
`backend/pytest.ini` : lancer simplement `pytest` depuis `backend/` affiche le
rapport de couverture.

## Couverture actuelle (mesurée le 2026-08-24)

```
pytest --cov=app --cov=vexa_agent --cov-report=term-missing
```

| Module | Couverture | Commentaire |
|---|---|---|
| `app/routes/auth.py` | 100% | Bien couvert (US-29) |
| `app/services/jwt.py` | 95% | Bien couvert (US-29) |
| `app/services/password.py` | 100% | Bien couvert (US-29) |
| `app/dependencies.py` | 64% | Chemins d'erreur (token invalide) non testés |
| `app/exceptions.py` | 83% | - |
| `app/routes/users.py` | 47% | Aucun test |
| `app/routes/recording.py` (visio) | 27% | Aucun test |
| `vexa_agent.py` (visio) | 25% | Aucun test |
| `app/routes/dictaphone.py` | 24% | Aucun test |
| `app/services/whisper_service.py` | 46% | Aucun test |
| `app/services/pyannote_service.py` | 44% | Aucun test |
| `app/services/speaker_assignment_service.py` | 11% | Aucun test |
| `app/services/llm_service.py` | 23% | Aucun test |
| `app/routes/summary.py` | 41% | Aucun test |
| `app/routes/actions.py` | 32% | Aucun test |
| `app/routes/action_status.py` | 52% | Aucun test |
| `app/routes/meetings.py` | 42% | Aucun test |
| **Total projet** | **55%** | Porté quasi entièrement par le module auth |

**Constat principal** : le module auth (US-29) est le seul à avoir une vraie
suite de tests. Toutes les autres briques (visio, dictaphone, LLM, dashboard)
n'ont aucun test à ce jour, alors qu'elles concentrent la logique la plus
complexe et la plus sujette aux régressions du projet (voir les bugs de
schéma déjà rencontrés sur `TranscriptSegment` pendant le Sprint 2).

## Fonctions critiques par module

### Auth (déjà couvert, US-29)

- `register` / `login` (`app/routes/auth.py`) — inscription et connexion.
- `create_access_token` / `decode_access_token` (`app/services/jwt.py`).
- `hash_password` / `verify_password` (`app/services/password.py`).
- `get_current_user` (`app/dependencies.py`) — chemins d'erreur (token
  expiré, token invalide, utilisateur supprimé) non couverts.

### Visio (Personne 2)

- `VexaAgent.send_bot` / `stop_bot` / `get_transcript` /
  `get_diarized_segments` (`vexa_agent.py`) — conversion des erreurs
  `requests` en `VexaConnectionError`.
- `_deduplicate_segments` (`app/routes/recording.py`) — déduplication des
  segments cumulatifs retournés par Vexa ; logique pure, facile à tester
  unitairement.
- `_save_diarized_segments` (`app/routes/recording.py`) — création des
  locuteurs et persistance des segments, y compris la non-duplication d'un
  locuteur déjà connu.
- Routes `start_recording` / `stop_recording` / `refresh_transcript` /
  `list_recordings` — en particulier l'isolation par utilisateur et le
  comportement en cas de `VexaConnectionError`.

### Dictaphone (Personne 3)

- `WhisperService.transcribe` / `transcribe_segments`
  (`app/services/whisper_service.py`).
- `PyannoteService.diarize` / `_to_wav`
  (`app/services/pyannote_service.py`) — notamment la conversion FFmpeg et
  la gestion d'un fichier audio invalide.
- `SpeakerAssignmentService.assign_speakers`
  (`app/services/speaker_assignment_service.py`) — croisement des segments
  Whisper avec les intervalles pyannote par recouvrement temporel ; logique
  pure, priorité haute pour un premier test (aucune dépendance externe).
- Route `upload_and_diarize` (`app/routes/dictaphone.py`) — enchaînement
  upload → transcription → diarisation → sauvegarde, y compris les cas
  d'échec à chaque étape.

### LLM + Dashboard (Personne 4)

- `LLMService.generate_summary` / `generate_structured_summary` /
  `_parse_structured_response` (`app/services/llm_service.py`) — en
  particulier le retry sur JSON mal formé et le retour `None` sur erreur
  API, sans jamais lever d'exception.
- `_match_speaker` / `_parse_due_date` (`app/routes/actions.py`) — logique
  pure de rapprochement responsable → locuteur et parsing de date ; priorité
  haute pour un premier test (aucune dépendance externe).
- Routes `extract_actions`, `update_action_status`, `list_meetings` (filtres
  thème/date), `get_meeting_details`, `get_open_actions`.

## Zones non couvertes à traiter en priorité

Par ordre de priorité (logique pure et sans dépendance externe d'abord,
la plus rapide à tester et la plus rentable) :

1. `_deduplicate_segments`, `_match_speaker`, `_parse_due_date`,
   `SpeakerAssignmentService.assign_speakers` — fonctions pures, aucun mock
   nécessaire.
2. `LLMService._parse_structured_response` — parsing et validation du JSON,
   testable avec des chaînes de test sans appeler l'API TogetherAI.
3. `get_current_user` — chemins d'erreur (token expiré, invalide, utilisateur
   supprimé).
4. Les flux complets visio et dictaphone (`VexaAgent`, routes
   `recording.py`/`dictaphone.py`) — nécessitent de mocker les appels
   externes (Vexa, Whisper, pyannote) ; couverts par les tickets dédiés
   US-50 (`vexa-integration-tests`) et US-54 (`transcript-parsing-tests`) au
   Sprint 3.
5. Les routes CRUD simples (`users.py`, `actions.py`, `action_status.py`,
   `meetings.py`) — tests d'intégration via le client de test FastAPI,
   suivant le modèle déjà en place dans `tests/test_auth.py`.

## Répartition par membre

Chaque membre est responsable d'amener sa propre brique à 70% de couverture
sur ses fonctions critiques listées ci-dessus, au rythme des tickets de tests
déjà prévus au backlog :

- **Visio** : US-50 (`vexa-integration-tests`, Sprint 3).
- **Dictaphone** : US-54 (`transcript-parsing-tests`, Sprint 3).
- **LLM + Dashboard** : US-59 (`json-extraction-tests`, Sprint 3).
- **Scrum Master (auth)** : déjà à 100% sur les routes ; reste à couvrir les
  chemins d'erreur de `get_current_user`.
