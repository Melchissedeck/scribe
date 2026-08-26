import { getMeetings, ApiError } from './api.js';

const meetingGrid = document.getElementById('meeting-grid');
const emptyState  = document.getElementById('empty-state');
const errorState  = document.getElementById('error-state');

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

loadMeetings();

async function loadMeetings() {
  try {
    const meetings = await getMeetings();
    renderMeetings(meetings);
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    errorState.hidden = false;
  }
}

function renderMeetings(meetings) {
  if (meetings.length === 0) {
    emptyState.hidden = false;
    return;
  }

  meetings.forEach((meeting) => {
    const card = document.createElement('div');
    card.className = 'card session-card';
    card.addEventListener('click', () => {
      window.location.href = `meeting-detail.html?id=${meeting.id}`;
    });

    card.innerHTML = `
      <div class="session-top">
        <div class="session-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
        </div>
        <div style="flex:1;min-width:0;">
          <div class="session-title">${escape(meeting.theme || 'Réunion sans titre')}</div>
          <div class="session-date">${formatDate(meeting.date)}</div>
        </div>
      </div>
      <p class="session-desc">${escape(meeting.summary_excerpt || 'Compte-rendu non encore disponible.')}</p>
      <div class="session-footer">
        <button class="ghost-btn">Voir le compte-rendu</button>
      </div>
    `;

    card.querySelector('.ghost-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      window.location.href = `meeting-detail.html?id=${meeting.id}`;
    });

    meetingGrid.appendChild(card);
  });
}

function formatDate(isoString) {
  const utc = isoString.endsWith('Z') || isoString.includes('+') ? isoString : isoString + 'Z';
  const date = new Date(utc);
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function escape(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
