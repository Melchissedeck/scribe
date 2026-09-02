"""
Test de charge — Traitement audio dictaphone (US-70)
Simule N uploads + transcriptions de fichiers audio en parallèle et mesure
les temps de réponse à chaque étape du pipeline (upload, découpage +
transcription Whisper, lancement de la diarisation).

Usage (script standalone):
    python backend/tests/test_load_audio.py

Variables d'environnement:
    LOAD_TEST_BASE_URL           URL de base de l'API
                                  (défaut: https://scribe-production-a094.up.railway.app)
    LOAD_TEST_USER1_EMAIL        Email du compte de test (obligatoire)
    LOAD_TEST_USER1_PASSWORD     Mot de passe du compte de test (obligatoire)
    LOAD_TEST_AUDIO_N_FILES      Nombre de fichiers traités en parallèle (défaut: 3)
    LOAD_TEST_AUDIO_DURATION_S   Durée de chaque fichier audio de test, en secondes (défaut: 60)
    LOAD_TEST_AUDIO_WAIT_DIARIZE Si "1", attend la fin complète de la diarisation
                                  (peut prendre plusieurs dizaines de minutes sur
                                  les ressources CPU actuelles) au lieu de ne
                                  mesurer que le lancement (défaut: 0)

La consommation mémoire serveur n'est pas mesurable depuis ce script (pas de
route d'introspection exposée) : elle s'observe via l'onglet Metrics de
Railway pendant l'exécution du test. Voir docs/load-tests.md pour les
relevés déjà effectués.
"""

import asyncio
import math
import os
import statistics
import struct
import time
import wave
from dataclasses import dataclass, field
from io import BytesIO

import httpx

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_URL       = os.getenv('LOAD_TEST_BASE_URL', 'https://scribe-production-a094.up.railway.app')
N_FILES        = int(os.getenv('LOAD_TEST_AUDIO_N_FILES', '3'))
AUDIO_DURATION_S = int(os.getenv('LOAD_TEST_AUDIO_DURATION_S', '60'))
WAIT_DIARIZE   = os.getenv('LOAD_TEST_AUDIO_WAIT_DIARIZE', '0') == '1'

USER_EMAIL    = os.getenv('LOAD_TEST_USER1_EMAIL', '')
USER_PASSWORD = os.getenv('LOAD_TEST_USER1_PASSWORD', '')

HTTP_TIMEOUT = 60.0  # secondes ; le lancement de la diarisation répond en <1s
                      # (traitement en tâche de fond, voir US-70bis)
DIARIZE_POLL_INTERVAL_S = 5.0

# ── Génération d'un fichier audio de test ───────────────────────────────────────

def _make_test_wav(duration_s: int, frame_rate: int = 16000) -> bytes:
    """Génère un WAV mono synthétique en mémoire, sans dépendance à ffmpeg."""
    buffer = BytesIO()
    with wave.open(buffer, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(frame_rate)
        frames = bytearray()
        for i in range(frame_rate * duration_s):
            t = i / frame_rate
            value = int(3000 * math.sin(2 * math.pi * 220 * t)) if (i // frame_rate) % 3 < 2 else 0
            frames += struct.pack('<h', value)
        wav_file.writeframes(bytes(frames))
    return buffer.getvalue()


# ── Résultats ──────────────────────────────────────────────────────────────────

@dataclass
class FileResult:
    file_id: int
    upload_ms: float = 0.0
    transcribe_ms: float = 0.0
    diarize_kickoff_ms: float = 0.0
    diarize_total_ms: float | None = None
    errors: list[str] = field(default_factory=list)
    recording_id: int | None = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# ── Helpers ────────────────────────────────────────────────────────────────────

async def login(client: httpx.AsyncClient) -> str | None:
    try:
        r = await client.post(f'{BASE_URL}/auth/login', json={
            'email': USER_EMAIL, 'password': USER_PASSWORD,
        })
        r.raise_for_status()
        return r.json().get('access_token')
    except Exception:
        return None


async def process_file(file_id: int, token: str, audio_bytes: bytes) -> FileResult:
    result = FileResult(file_id=file_id)
    headers = {'Authorization': f'Bearer {token}'}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, verify=False) as client:
        # 1. Créer l'enregistrement
        try:
            r = await client.post(f'{BASE_URL}/meetings', headers=headers)
            r.raise_for_status()
            result.recording_id = r.json()['recording_id']
        except Exception as exc:
            result.errors.append(f'create_failed: {exc}')
            return result

        rid = result.recording_id

        # 2. Upload de l'audio
        try:
            t0 = time.perf_counter()
            r = await client.post(
                f'{BASE_URL}/meetings/{rid}/upload-audio',
                headers=headers,
                files={'audio': (f'loadtest_{file_id}.wav', audio_bytes, 'audio/wav')},
            )
            result.upload_ms = (time.perf_counter() - t0) * 1000
            r.raise_for_status()
        except Exception as exc:
            result.errors.append(f'upload_failed: {exc}')
            return result

        # 3. Transcription (découpage + appel Whisper)
        try:
            t0 = time.perf_counter()
            r = await client.post(f'{BASE_URL}/meetings/{rid}/transcribe', headers=headers)
            result.transcribe_ms = (time.perf_counter() - t0) * 1000
            r.raise_for_status()
        except Exception as exc:
            result.errors.append(f'transcribe_failed: {exc}')
            return result

        # 4. Lancement de la diarisation (tâche de fond, réponse immédiate)
        try:
            t0 = time.perf_counter()
            r = await client.post(f'{BASE_URL}/meetings/{rid}/diarize', headers=headers)
            result.diarize_kickoff_ms = (time.perf_counter() - t0) * 1000
            r.raise_for_status()
        except Exception as exc:
            result.errors.append(f'diarize_kickoff_failed: {exc}')
            return result

        # 5. (optionnel) Attente de la fin complète de la diarisation
        if WAIT_DIARIZE:
            t0 = time.perf_counter()
            while True:
                try:
                    r = await client.get(f'{BASE_URL}/meetings/{rid}/diarize-status', headers=headers)
                    status = r.json().get('status')
                except Exception:
                    status = None
                if status in ('done', 'failed'):
                    result.diarize_total_ms = (time.perf_counter() - t0) * 1000
                    if status == 'failed':
                        result.errors.append('diarize_failed')
                    break
                await asyncio.sleep(DIARIZE_POLL_INTERVAL_S)

    return result


# ── Rapport ────────────────────────────────────────────────────────────────────

def percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    idx = int(len(data_sorted) * p / 100)
    return data_sorted[min(idx, len(data_sorted) - 1)]


def print_stats(label: str, times: list[float]) -> None:
    if not times:
        print(f'  {label:30s} : aucune donnée')
        return
    print(f'  {label:30s} : '
          f'moy={statistics.mean(times):.0f}ms  '
          f'p50={percentile(times, 50):.0f}ms  '
          f'max={max(times):.0f}ms')


def print_report(results: list[FileResult], total_elapsed: float) -> None:
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    print('\n' + '=' * 60)
    print('  RESULTATS DU TEST DE CHARGE - TRAITEMENT AUDIO')
    print('=' * 60)
    print(f'  Fichiers traités   : {len(results)} ({AUDIO_DURATION_S}s chacun)')
    print(f'  Succès             : {len(successes)}')
    print(f'  Échecs             : {len(failures)}')
    print(f'  Taux d\'échec       : {len(failures) / len(results) * 100:.1f}%')
    print(f'  Durée totale       : {total_elapsed:.1f}s')
    print()

    if failures:
        print('  Erreurs détectées :')
        for r in failures:
            print(f'    Fichier {r.file_id:02d} → {", ".join(r.errors)}')
        print()

    print('  Temps de réponse :')
    print_stats('POST /upload-audio', [r.upload_ms for r in results if r.upload_ms > 0])
    print_stats('POST /transcribe', [r.transcribe_ms for r in results if r.transcribe_ms > 0])
    print_stats('POST /diarize (lancement)', [r.diarize_kickoff_ms for r in results if r.diarize_kickoff_ms > 0])
    if WAIT_DIARIZE:
        diarize_totals = [r.diarize_total_ms for r in results if r.diarize_total_ms]
        print_stats('Diarisation (bout en bout)', diarize_totals)
    print('=' * 60)


# ── Point d'entrée ─────────────────────────────────────────────────────────────

async def main() -> None:
    if not (USER_EMAIL and USER_PASSWORD):
        print('ERREUR : Aucun compte configuré.')
        print('Renseignez LOAD_TEST_USER1_EMAIL et LOAD_TEST_USER1_PASSWORD.')
        return

    print(f'Lancement de {N_FILES} traitement(s) audio simultané(s) sur {BASE_URL}')
    print(f'Durée par fichier : {AUDIO_DURATION_S}s | Attente diarisation complète : {WAIT_DIARIZE}')
    print()

    audio_bytes = _make_test_wav(AUDIO_DURATION_S)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, verify=False) as client:
        token = await login(client)
    if not token:
        print('ERREUR : Échec de connexion avec le compte fourni.')
        return

    t0 = time.perf_counter()
    tasks = [process_file(i, token, audio_bytes) for i in range(N_FILES)]
    results = await asyncio.gather(*tasks)
    total_elapsed = time.perf_counter() - t0

    print_report(list(results), total_elapsed)


if __name__ == '__main__':
    asyncio.run(main())
