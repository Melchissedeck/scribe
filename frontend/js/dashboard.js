// Logique de la page dashboard listant les reunions passees

import { getMeetings, ApiError } from './api.js';
import './theme.js';

const meetingListEl = document.getElementById('meeting-list');
const emptyStateEl = document.getElementById('empty-state');
const meetingCountEl = document.getElementById('meeting-count');

requireAuth();
loadMeetings();

function requireAuth() {
  // Redirige vers la connexion si aucun token n'est present
  const token = sessionStorage.getItem('access_token');
  if (!token) {
    window.location.href = 'login.html';
  }
}

async function loadMeetings() {
  try {
    const meetings = await getMeetings();
    renderMeetings(meetings);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    meetingListEl.textContent = 'Impossible de charger vos réunions pour le moment.';
  }
}

function renderMeetings(meetings) {
  meetingCountEl.textContent = `${meetings.length} réunion${meetings.length > 1 ? 's' : ''}`;

  if (meetings.length === 0) {
    emptyStateEl.hidden = false;
    return;
  }

  meetingListEl.innerHTML = '';

  meetings.forEach((meeting) => {
    const link = document.createElement('a');
    link.className = 'meeting-item card';
    link.href = `meeting-detail.html?id=${meeting.id}`;

    const theme = document.createElement('p');
    theme.className = 'meeting-theme';
    theme.textContent = meeting.theme || 'Réunion sans titre';

    const date = document.createElement('p');
    date.className = 'meeting-date';
    date.textContent = formatDate(meeting.date);

    const excerpt = document.createElement('p');
    excerpt.className = 'meeting-excerpt';
    excerpt.textContent = meeting.summary_excerpt || 'Compte-rendu non encore disponible.';

    link.appendChild(theme);
    link.appendChild(date);
    link.appendChild(excerpt);
    meetingListEl.appendChild(link);
  });
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}