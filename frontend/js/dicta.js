import { requireConsent } from './consent.js';

requireConsent();

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}


// ─────────────────────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────────────────────

const API_BASE_URL = 'https://127.0.0.1:8000';


// ─────────────────────────────────────────────────────────────────────────────
// DOM
// ─────────────────────────────────────────────────────────────────────────────

const recordingView = document.getElementById('recording-view');
const transcriptionView = document.getElementById('transcription-view');

const startButton = document.getElementById('start-recording-button');
const stopButton = document.getElementById('stop-recording-button');
const newRecordingButton = document.getElementById('new-recording-button');

const recordingIndicator = document.getElementById('recording-indicator');
const recordingStatus = document.getElementById('recording-status');
const recordingTimer = document.getElementById('recording-timer');
const recordingError = document.getElementById('recording-error');

const transcriptionStatus = document.getElementById('transcription-status');
const transcriptionLoading = document.getElementById('transcription-loading');
const transcriptionResult = document.getElementById('transcription-result');
const transcriptionContent = document.getElementById('transcription-content');
const transcriptionError = document.getElementById('transcription-error');


// ─────────────────────────────────────────────────────────────────────────────
// État
// ─────────────────────────────────────────────────────────────────────────────

let mediaRecorder = null;
let audioChunks = [];
let mediaStream = null;

let currentRecordingId = null;

let timerInterval = null;
let elapsedSeconds = 0;


// ─────────────────────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────────────────────

async function apiRequest(path, options = {}) {
  const token = sessionStorage.getItem('access_token');

  const response = await fetch(API_BASE_URL + path, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data && data.detail
        ? data.detail
        : 'Une erreur est survenue.';

    throw new Error(message);
  }

  return data;
}


// ─────────────────────────────────────────────────────────────────────────────
// Création du recording
// ─────────────────────────────────────────────────────────────────────────────

async function createRecording() {
  return apiRequest('/meetings', {
    method: 'POST',
  });
}


// ─────────────────────────────────────────────────────────────────────────────
// Upload de l'audio
// ─────────────────────────────────────────────────────────────────────────────

async function uploadAudio(recordingId, audioBlob) {
  const extension = audioBlob.type.includes('webm')
    ? 'webm'
    : 'webm';

  const formData = new FormData();

  formData.append(
    'audio',
    audioBlob,
    `recording.${extension}`,
  );

  const token = sessionStorage.getItem('access_token');

  const response = await fetch(
    `${API_BASE_URL}/meetings/${recordingId}/upload-audio`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    },
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data && data.detail
        ? data.detail
        : 'Impossible d’envoyer l’audio.';

    throw new Error(message);
  }

  return data;
}


// ─────────────────────────────────────────────────────────────────────────────
// Transcription
// ─────────────────────────────────────────────────────────────────────────────

async function transcribeAudio(recordingId) {
  return apiRequest(`/meetings/${recordingId}/transcribe`, {
    method: 'POST',
  });
}


// ─────────────────────────────────────────────────────────────────────────────
// Timer
// ─────────────────────────────────────────────────────────────────────────────

function startTimer() {
  stopTimer();

  elapsedSeconds = 0;
  updateTimerDisplay();

  timerInterval = setInterval(() => {
    elapsedSeconds += 1;
    updateTimerDisplay();
  }, 1000);
}


function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}


function updateTimerDisplay() {
  const minutes = String(
    Math.floor(elapsedSeconds / 60),
  ).padStart(2, '0');

  const seconds = String(
    elapsedSeconds % 60,
  ).padStart(2, '0');

  recordingTimer.textContent = `${minutes}:${seconds}`;
}


// ─────────────────────────────────────────────────────────────────────────────
// Affichage des vues
// ─────────────────────────────────────────────────────────────────────────────

function showRecordingView() {
  recordingView.classList.remove('visio-hidden');
  transcriptionView.classList.add('visio-hidden');
}


function showTranscriptionView() {
  recordingView.classList.add('visio-hidden');
  transcriptionView.classList.remove('visio-hidden');
}


// ─────────────────────────────────────────────────────────────────────────────
// Réinitialisation des messages
// ─────────────────────────────────────────────────────────────────────────────

function clearRecordingError() {
  recordingError.textContent = '';
}


function clearTranscriptionError() {
  transcriptionError.textContent = '';
}


// ─────────────────────────────────────────────────────────────────────────────
// Commencer l'enregistrement
// ─────────────────────────────────────────────────────────────────────────────

startButton.addEventListener('click', async () => {
  clearRecordingError();

  startButton.disabled = true;
  startButton.textContent = 'Préparation...';

  try {
    // 1. Crée l'enregistrement en base
    const recording = await createRecording();

    currentRecordingId = recording.recording_id;

    // 2. Demande l'accès au microphone
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });

    // 3. Vérifie le format supporté par le navigateur
    let mimeType = '';

    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      mimeType = 'audio/webm;codecs=opus';
    } else if (MediaRecorder.isTypeSupported('audio/webm')) {
      mimeType = 'audio/webm';
    }

    // 4. Crée le MediaRecorder
    mediaRecorder = mimeType
      ? new MediaRecorder(mediaStream, { mimeType })
      : new MediaRecorder(mediaStream);

    audioChunks = [];

    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener('stop', handleRecordingStop);

    // 5. Lance l'enregistrement
    mediaRecorder.start();

    recordingStatus.textContent = 'Enregistrement en cours...';
    recordingIndicator.classList.add('recording-indicator--active');

    startButton.disabled = true;
    stopButton.disabled = false;

    startTimer();

  } catch (error) {
    console.error(error);

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    currentRecordingId = null;

    recordingStatus.textContent = 'Prêt à enregistrer';
    recordingIndicator.classList.remove(
      'recording-indicator--active',
    );

    startButton.disabled = false;
    startButton.textContent = 'Commencer l’enregistrement';
    stopButton.disabled = true;

    recordingError.textContent =
      error.message ||
      'Impossible de démarrer l’enregistrement.';
  }
});


// ─────────────────────────────────────────────────────────────────────────────
// Arrêter l'enregistrement
// ─────────────────────────────────────────────────────────────────────────────

stopButton.addEventListener('click', () => {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    return;
  }

  stopButton.disabled = true;
  stopButton.textContent = 'Arrêt...';

  stopTimer();

  mediaRecorder.stop();

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  recordingIndicator.classList.remove(
    'recording-indicator--active',
  );

  recordingStatus.textContent = 'Enregistrement terminé';
});


// ─────────────────────────────────────────────────────────────────────────────
// Traitement après arrêt du MediaRecorder
// ─────────────────────────────────────────────────────────────────────────────

async function handleRecordingStop() {
  try {
    if (!currentRecordingId) {
      throw new Error(
        'Aucun enregistrement n’a été créé.',
      );
    }

    if (audioChunks.length === 0) {
      throw new Error(
        'Aucun audio n’a été enregistré.',
      );
    }

    // Création du fichier audio
    const audioBlob = new Blob(
      audioChunks,
      {
        type: mediaRecorder.mimeType || 'audio/webm',
      },
    );

    showTranscriptionView();

    transcriptionLoading.classList.remove(
      'visio-hidden',
    );

    transcriptionResult.classList.add(
      'visio-hidden',
    );

    transcriptionStatus.textContent =
      'Envoi de l’audio...';

    clearTranscriptionError();

    // Upload
    await uploadAudio(
      currentRecordingId,
      audioBlob,
    );

    // Transcription
    transcriptionStatus.textContent =
      'Transcription en cours...';

    const result = await transcribeAudio(
      currentRecordingId,
    );

    // Affichage du résultat
    transcriptionLoading.classList.add(
      'visio-hidden',
    );

    transcriptionResult.classList.remove(
      'visio-hidden',
    );

    transcriptionStatus.textContent =
      'Transcription terminée';

    transcriptionContent.textContent =
      result.transcript ||
      '(Aucune transcription disponible)';

  } catch (error) {
    console.error(error);

    transcriptionLoading.classList.add(
      'visio-hidden',
    );

    transcriptionStatus.textContent =
      'La transcription a échoué.';

    transcriptionError.textContent =
      error.message ||
      'Une erreur est survenue pendant la transcription.';

  } finally {
    audioChunks = [];

    if (mediaRecorder) {
      mediaRecorder = null;
    }
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// Nouvel enregistrement
// ─────────────────────────────────────────────────────────────────────────────

newRecordingButton.addEventListener('click', () => {
  currentRecordingId = null;

  elapsedSeconds = 0;
  updateTimerDisplay();

  recordingStatus.textContent = 'Prêt à enregistrer';

  recordingIndicator.classList.remove(
    'recording-indicator--active',
  );

  startButton.disabled = false;
  startButton.textContent = 'Commencer l’enregistrement';

  stopButton.disabled = true;
  stopButton.textContent = 'Arrêter';

  clearRecordingError();
  clearTranscriptionError();

  transcriptionContent.textContent = '';

  showRecordingView();
});