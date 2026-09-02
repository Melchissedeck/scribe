import { requireConsent } from './consent.js';
import './theme.js';
import {
  startRecording, stopRecording, refreshTranscript,
  getSpeakingTime, createDictaphoneRecording, uploadAudioFile, transcribeRecording,
  ApiError,
} from './api.js';

requireConsent();

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

// ── DOM refs ──────────────────────────────────────────────────────────────
const urlInput       = document.getElementById('meeting-url');
const startBtn       = document.getElementById('start-button');
const deployHint     = document.getElementById('deploy-hint');
const errorMsg       = document.getElementById('error-message');

const setupPanel     = document.getElementById('setup-panel');
const sessionPanel   = document.getElementById('session-panel');
const donePanel      = document.getElementById('done-panel');

const statusDot      = document.getElementById('status-dot');
const statusLabel    = document.getElementById('status-label');
const platformBadge  = document.getElementById('platform-badge');
const meetingIdDisp  = document.getElementById('meeting-id-display');
const transcriptEl        = document.getElementById('transcript-content');
const finalTranscript     = document.getElementById('final-transcript');
const detailLink          = document.getElementById('detail-link');
const sessionError        = document.getElementById('session-error');
const stopBtn             = document.getElementById('stop-button');
const elapsedEl           = document.getElementById('elapsed-time');
const fallbackSection     = document.getElementById('fallback-section');
const audioFileInput      = document.getElementById('audio-file-input');
const fileLabelText       = document.getElementById('file-label-text');
const uploadBtn           = document.getElementById('upload-button');
const uploadError         = document.getElementById('upload-error');
const speakingTimeSection = document.getElementById('speaking-time-section');
const speakingTimeList    = document.getElementById('speaking-time-list');

// ── State ─────────────────────────────────────────────────────────────────
let selectedPlatform   = null;
let currentRecordingId = null;
let pollInterval       = null;
let timerInterval      = null;
let elapsedSeconds     = 0;

const PLATFORM_LABELS = {
  google_meet: 'Google Meet',
  zoom:        'Zoom',
  teams:       'Teams',
};

// ── Platform selection ────────────────────────────────────────────────────
document.querySelectorAll('.platform-card').forEach((card) => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.platform-card').forEach((c) => c.classList.remove('selected'));
    card.classList.add('selected');
    selectedPlatform = card.dataset.platform;
    updateDeployButton();
  });
});

// ── URL input ─────────────────────────────────────────────────────────────
urlInput.addEventListener('input', () => {
  errorMsg.textContent = '';
  updateDeployButton();
});

function updateDeployButton() {
  const canDeploy = !!selectedPlatform && urlInput.value.trim().length > 0;
  startBtn.disabled = !canDeploy;
  deployHint.style.display = canDeploy ? 'none' : '';
}

function extractMeetingId(link) {
  const trimmed = link.trim().replace(/\/+$/, '');
  const lastSegment = trimmed.split('/').pop() || '';
  return lastSegment.split('?')[0];
}

// ── Start session ─────────────────────────────────────────────────────────
startBtn.addEventListener('click', async () => {
  if (!selectedPlatform || !urlInput.value.trim()) return;

  const rawUrl = urlInput.value.trim();
  const meetingId = extractMeetingId(rawUrl);
  if (!meetingId) {
    errorMsg.textContent = 'Lien de réunion invalide.';
    return;
  }

  startBtn.disabled = true;
  startBtn.textContent = 'Déploiement en cours…';
  errorMsg.textContent = '';

  try {
    const recording = await startRecording(selectedPlatform, meetingId, 'Scribe', rawUrl);
    currentRecordingId = recording.id;

    platformBadge.textContent = PLATFORM_LABELS[selectedPlatform] ?? selectedPlatform;
    meetingIdDisp.textContent  = meetingId;

    showPanel(sessionPanel);
    startElapsedTimer();
    startPolling();
  } catch (err) {
    errorMsg.textContent = err instanceof ApiError ? err.message : 'Impossible de lancer la session.';
    startBtn.disabled = false;
    startBtn.textContent = "Déployer l'agent";
    if (!(err instanceof ApiError && err.status === 422)) {
      fallbackSection.classList.remove('visio-hidden');
    }
  }
});

// ── Stop session ──────────────────────────────────────────────────────────
stopBtn.addEventListener('click', async () => {
  stopBtn.disabled = true;
  stopBtn.textContent = 'Arrêt en cours…';
  sessionError.textContent = '';

  clearInterval(pollInterval);
  clearInterval(timerInterval);

  try {
    const recording = await stopRecording(currentRecordingId);

    statusDot.classList.add('status-dot--stopped');
    statusLabel.textContent = 'Session arrêtée';

    finalTranscript.textContent = recording.transcript || transcriptEl.textContent || '(Aucune transcription disponible)';
    detailLink.href = `meeting-detail.html?id=${recording.id}`;
    loadSpeakingTime(currentRecordingId);
    showPanel(donePanel);
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      sessionStorage.removeItem('access_token');
      window.location.href = 'login.html';
      return;
    }
    sessionError.textContent = err instanceof ApiError ? err.message : "Erreur lors de l'arrêt.";
    stopBtn.disabled = false;
    stopBtn.textContent = 'Arrêter la session';
    startPolling();
    startElapsedTimer();
  }
});

// ── Speaking time ─────────────────────────────────────────────────────────
async function loadSpeakingTime(recordingId) {
  try {
    const data = await getSpeakingTime(recordingId);
    if (!data.entries || data.entries.length === 0) return;
    speakingTimeList.innerHTML = data.entries.map((e) => {
      const mins = Math.floor(e.seconds / 60);
      const secs = Math.round(e.seconds % 60);
      const label = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
      return `
        <div class="speaking-time-entry">
          <div class="speaking-time-meta">
            <span class="speaking-time-name">${e.speaker}</span>
            <span class="speaking-time-value">${label} · ${e.percentage}%</span>
          </div>
          <div class="speaking-time-bar-track">
            <div class="speaking-time-bar" style="width: ${e.percentage}%"></div>
          </div>
        </div>`;
    }).join('');
    speakingTimeSection.classList.remove('visio-hidden');
  } catch (_) {
    // silently skip if stats unavailable
  }
}

// ── Polling transcript ────────────────────────────────────────────────────
function startPolling() {
  pollInterval = setInterval(async () => {
    try {
      const recording = await refreshTranscript(currentRecordingId);
      if (recording.transcript) {
        transcriptEl.textContent = recording.transcript;
        transcriptEl.scrollTop = transcriptEl.scrollHeight;
      }
    } catch (_) {
      // keep polling silently on transient errors
    }
  }, 2000);
}

// ── Elapsed timer ─────────────────────────────────────────────────────────
function startElapsedTimer() {
  elapsedSeconds = 0;
  timerInterval = setInterval(() => {
    elapsedSeconds++;
    const m = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
    const s = String(elapsedSeconds % 60).padStart(2, '0');
    elapsedEl.textContent = `${m}:${s}`;
  }, 1000);
}

// ── Fallback audio upload ─────────────────────────────────────────────────
audioFileInput.addEventListener('change', () => {
  const file = audioFileInput.files[0];
  fileLabelText.textContent = file ? file.name : 'Choisir un fichier audio';
  uploadBtn.disabled = !file;
});

uploadBtn.addEventListener('click', async () => {
  const file = audioFileInput.files[0];
  if (!file) return;

  uploadBtn.disabled = true;
  uploadBtn.textContent = 'Envoi en cours…';
  uploadError.textContent = '';

  try {
    const { recording_id } = await createDictaphoneRecording();
    await uploadAudioFile(recording_id, file);
    uploadBtn.textContent = 'Transcription en cours…';
    const result = await transcribeRecording(recording_id);
    finalTranscript.textContent = result.transcript || '(Aucune transcription disponible)';
    detailLink.href = `meeting-detail.html?id=${recording_id}`;
    showPanel(donePanel);
  } catch (err) {
    uploadError.textContent = err instanceof ApiError ? err.message : "Erreur lors de l'upload.";
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Transcrire le fichier';
  }
});

// ── Panel switching ───────────────────────────────────────────────────────
function showPanel(panel) {
  setupPanel.classList.add('visio-hidden');
  sessionPanel.classList.add('visio-hidden');
  donePanel.classList.add('visio-hidden');
  panel.classList.remove('visio-hidden');
}
