"""
Test de charge — Réunions visio simultanées
Simule N démarrages de session visio en parallèle et mesure les temps de réponse.

Usage (script standalone):
    python backend/tests/test_load_visio.py

Variables d'environnement:
    LOAD_TEST_BASE_URL          URL de base de l'API
                                (défaut: https://scribe-production-a094.up.railway.app)
    LOAD_TEST_USER1_EMAIL       Email du compte de test n°1 (obligatoire)
    LOAD_TEST_USER1_PASSWORD    Mot de passe du compte n°1 (obligatoire)
    LOAD_TEST_USER2_EMAIL       Email du compte n°2 (optionnel)
    LOAD_TEST_USER2_PASSWORD    Mot de passe du compte n°2 (optionnel)
    LOAD_TEST_N_SESSIONS        Nombre de sessions simultanées (défaut: 5)
    LOAD_TEST_PLATFORM          Plateforme: google_meet | zoom | teams (défaut: google_meet)
    LOAD_TEST_MEETING_ID        ID de réunion à utiliser (défaut: abc-defg-hij, URL fictive)
    LOAD_TEST_MEETING_URL       URL complète de réunion (prioritaire sur MEETING_ID)
"""

import asyncio
import os
import statistics
import time
from dataclasses import dataclass, field

import httpx

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_URL        = os.getenv('LOAD_TEST_BASE_URL', 'https://scribe-production-a094.up.railway.app')
N_SESSIONS      = int(os.getenv('LOAD_TEST_N_SESSIONS', '5'))
PLATFORM        = os.getenv('LOAD_TEST_PLATFORM', 'google_meet')
MEETING_ID      = os.getenv('LOAD_TEST_MEETING_ID', 'abc-defg-hij')
MEETING_URL     = os.getenv('LOAD_TEST_MEETING_URL', '')

USERS = []

u1_email    = os.getenv('LOAD_TEST_USER1_EMAIL', '')
u1_password = os.getenv('LOAD_TEST_USER1_PASSWORD', '')
u1_url      = os.getenv('LOAD_TEST_USER1_MEETING_URL', MEETING_URL)
if u1_email and u1_password:
    USERS.append({'email': u1_email, 'password': u1_password, 'meeting_url': u1_url})

u2_email    = os.getenv('LOAD_TEST_USER2_EMAIL', '')
u2_password = os.getenv('LOAD_TEST_USER2_PASSWORD', '')
u2_url      = os.getenv('LOAD_TEST_USER2_MEETING_URL', MEETING_URL)
if u2_email and u2_password:
    USERS.append({'email': u2_email, 'password': u2_password, 'meeting_url': u2_url})

HTTP_TIMEOUT = 30.0  # secondes

# ── Résultats ──────────────────────────────────────────────────────────────────

@dataclass
class SessionResult:
    session_id: int
    login_ms: float = 0.0
    start_ms: float = 0.0
    stop_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    recording_id: int | None = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# ── Helpers ────────────────────────────────────────────────────────────────────

async def login(client: httpx.AsyncClient, email: str, password: str) -> tuple[str | None, float]:
    try:
        t0 = time.perf_counter()
        r = await client.post(f'{BASE_URL}/auth/login', json={'email': email, 'password': password})
        elapsed = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        return r.json().get('access_token'), elapsed
    except Exception:
        return None, 0.0


async def start_recording(client: httpx.AsyncClient, token: str, meeting_url: str = '') -> tuple[int | None, float]:
    payload: dict = {'platform': PLATFORM, 'native_meeting_id': MEETING_ID, 'bot_name': 'ScribeLoadTest'}
    url = meeting_url or MEETING_URL
    if url:
        payload['meeting_url'] = url

    headers = {'Authorization': f'Bearer {token}'}
    try:
        t0 = time.perf_counter()
        r = await client.post(f'{BASE_URL}/recording/start', json=payload, headers=headers)
        elapsed = (time.perf_counter() - t0) * 1000
        if r.status_code in (200, 201):
            return r.json().get('id'), elapsed
        return None, elapsed
    except Exception:
        return None, 0.0


async def stop_recording(client: httpx.AsyncClient, token: str, recording_id: int) -> tuple[bool, float]:
    headers = {'Authorization': f'Bearer {token}'}
    try:
        t0 = time.perf_counter()
        r = await client.post(f'{BASE_URL}/recording/{recording_id}/stop', headers=headers)
        elapsed = (time.perf_counter() - t0) * 1000
        return r.status_code in (200, 201), elapsed
    except Exception:
        return False, 0.0


# ── Session complète ───────────────────────────────────────────────────────────

async def run_session(session_id: int, user: dict) -> SessionResult:
    result = SessionResult(session_id=session_id)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, verify=False) as client:
        # 1. Login
        token, result.login_ms = await login(client, user['email'], user['password'])
        if not token:
            result.errors.append('login_failed')
            return result

        # 2. Démarrer la réunion
        recording_id, result.start_ms = await start_recording(client, token, user.get('meeting_url', ''))
        if not recording_id:
            result.errors.append('start_failed')
            return result

        result.recording_id = recording_id

        # Simulation d'une réunion courte (5 secondes)
        await asyncio.sleep(5)

        # 3. Arrêter la réunion
        ok, result.stop_ms = await stop_recording(client, token, recording_id)
        if not ok:
            result.errors.append('stop_failed')

    return result


# ── Rapport ────────────────────────────────────────────────────────────────────

def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    idx = int(len(data_sorted) * p / 100)
    return data_sorted[min(idx, len(data_sorted) - 1)]


def print_report(results: list[SessionResult], total_elapsed: float) -> None:
    successes = [r for r in results if r.success]
    failures  = [r for r in results if not r.success]

    login_times = [r.login_ms for r in results if r.login_ms > 0]
    start_times = [r.start_ms for r in results if r.start_ms > 0]
    stop_times  = [r.stop_ms  for r in results if r.stop_ms  > 0]

    print('\n' + '=' * 60)
    print('  RESULTATS DU TEST DE CHARGE - REUNIONS VISIO')
    print('=' * 60)
    print(f'  Sessions lancées   : {len(results)}')
    print(f'  Succès             : {len(successes)}')
    print(f'  Échecs             : {len(failures)}')
    print(f'  Taux d\'échec       : {len(failures) / len(results) * 100:.1f}%')
    print(f'  Durée totale       : {total_elapsed:.1f}s')
    print()

    if failures:
        print('  Erreurs détectées :')
        for r in failures:
            print(f'    Session {r.session_id:02d} → {", ".join(r.errors)}')
        print()

    def print_stats(label: str, times: list[float]) -> None:
        if not times:
            print(f'  {label:25s} : aucune donnée')
            return
        print(f'  {label:25s} : '
              f'moy={statistics.mean(times):.0f}ms  '
              f'p50={percentile(times, 50):.0f}ms  '
              f'p95={percentile(times, 95):.0f}ms  '
              f'p99={percentile(times, 99):.0f}ms  '
              f'max={max(times):.0f}ms')

    print('  Temps de réponse :')
    print_stats('POST /auth/login', login_times)
    print_stats('POST /recording/start', start_times)
    print_stats('POST /recording/{id}/stop', stop_times)
    print('=' * 60)


# ── Point d'entrée ─────────────────────────────────────────────────────────────

async def main() -> None:
    if not USERS:
        print('ERREUR : Aucun compte configuré.')
        print('Renseignez LOAD_TEST_USER1_EMAIL et LOAD_TEST_USER1_PASSWORD.')
        return

    print(f'Lancement de {N_SESSIONS} session(s) simultanée(s) sur {BASE_URL}')
    print(f'Plateforme : {PLATFORM} | Meeting ID : {MEETING_URL or MEETING_ID}')
    print(f'Comptes disponibles : {len(USERS)}')
    print()

    tasks = [
        run_session(i, USERS[i % len(USERS)])
        for i in range(N_SESSIONS)
    ]

    t0 = time.perf_counter()
    results = await asyncio.gather(*tasks)
    total_elapsed = time.perf_counter() - t0

    print_report(list(results), total_elapsed)


if __name__ == '__main__':
    asyncio.run(main())
