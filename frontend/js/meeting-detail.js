// Logique de la page affichant le compte-rendu d'une reunion

import { getMeetingSummary, ApiError } from './api.js';

const themeEl = document.getElementById('meeting-theme');
const dateEl = document.getElementById('meeting-date');
const summaryEl = document.getElementById('meeting-summary');

requireAuth();
loadSummary();

function requireAuth() {
  const token = sessionStorage.getItem('access_token');
  if (!token) {
    window.location.href = 'login.html';
  }
}

function getMeetingIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

async function loadSummary() {
  const meetingId = getMeetingIdFromUrl();

  if (!meetingId) {
    summaryEl.textContent = "Aucune réunion sélectionnée.";
    return;
  }

  try {
    const result = await getMeetingSummary(meetingId);
    themeEl.textContent = 'Compte-rendu';
    dateEl.textContent = '';
    summaryEl.textContent = result.summary;
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    if (error instanceof ApiError && error.status === 404) {
      summaryEl.textContent = "Le compte-rendu n'est pas encore disponible pour cette réunion.";
      return;
    }
    summaryEl.textContent = "Impossible de charger le compte-rendu pour le moment.";
  }
}