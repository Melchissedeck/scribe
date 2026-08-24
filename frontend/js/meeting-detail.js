import { getMeetingDetails, updateActionStatus, ApiError } from './api.js';

const themeEl = document.getElementById('meeting-theme');
const dateEl = document.getElementById('meeting-date');
const summaryEl = document.getElementById('meeting-summary');
const speakersCard = document.getElementById('speakers-card');
const speakersTranscript = document.getElementById('speakers-transcript');
const actionsCard = document.getElementById('actions-card');
const actionsList = document.getElementById('actions-list');

const SPEAKER_COLORS = [
  { bg: '#EAF1FF', text: '#2563EB' },
  { bg: '#FEF3C7', text: '#92400E' },
  { bg: '#DCFCE7', text: '#166534' },
  { bg: '#FCE7F3', text: '#9D174D' },
  { bg: '#EDE9FE', text: '#5B21B6' },
  { bg: '#FFEDD5', text: '#9A3412' },
];

const STATUS_LABELS = {
  todo: 'À faire',
  in_progress: 'En cours',
  done: 'Terminé',
};

requireAuth();
loadMeetingData();

function requireAuth() {
  if (!sessionStorage.getItem('access_token')) {
    window.location.href = 'login.html';
  }
}

function getMeetingIdFromUrl() {
  return new URLSearchParams(window.location.search).get('id');
}

async function loadMeetingData() {
  const meetingId = getMeetingIdFromUrl();
  if (!meetingId) {
    summaryEl.textContent = 'Aucune réunion sélectionnée.';
    return;
  }

  try {
    const details = await getMeetingDetails(meetingId);
    renderSummary(details);
    renderSpeakers(details.segments);
    renderActions(details.actions);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    if (error instanceof ApiError && error.status === 404) {
      summaryEl.textContent = 'Réunion introuvable.';
      return;
    }
    summaryEl.textContent = 'Impossible de charger cette réunion pour le moment.';
  }
}

function renderSummary(details) {
  themeEl.textContent = details.theme || 'Compte-rendu';
  dateEl.textContent = new Date(details.started_at).toLocaleString('fr-FR');
  summaryEl.textContent = details.summary || "Le compte-rendu n'est pas encore disponible pour cette réunion.";
}

function renderSpeakers(segments) {
  if (!segments || segments.length === 0) return;

  const colorMap = {};
  let colorIndex = 0;

  segments.forEach((seg) => {
    if (!(seg.speaker_name in colorMap)) {
      colorMap[seg.speaker_name] = SPEAKER_COLORS[colorIndex % SPEAKER_COLORS.length];
      colorIndex++;
    }

    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;';

    const colors = colorMap[seg.speaker_name];
    const badge = document.createElement('span');
    badge.textContent = seg.speaker_name;
    badge.style.cssText = `
      flex-shrink:0;
      padding:3px 10px;
      border-radius:6px;
      font-size:11px;
      font-weight:700;
      letter-spacing:.03em;
      background:${colors.bg};
      color:${colors.text};
      margin-top:2px;
      white-space:nowrap;
    `;

    const text = document.createElement('p');
    text.textContent = seg.text;
    text.style.cssText = 'margin:0;font-size:13.5px;line-height:1.6;color:#334155;';

    row.appendChild(badge);
    row.appendChild(text);
    speakersTranscript.appendChild(row);
  });

  speakersCard.style.display = '';
}

function renderActions(actions) {
  if (!actions || actions.length === 0) return;

  actions.forEach((action) => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:12px;align-items:center;justify-content:space-between;margin-bottom:12px;';

    const text = document.createElement('p');
    text.textContent = action.description;
    text.style.cssText = 'margin:0;font-size:13.5px;line-height:1.5;color:#334155;flex:1;';

    const select = document.createElement('select');
    select.style.cssText = 'padding:6px 10px;border:1px solid #E2E8F0;border-radius:8px;font-size:12px;';
    Object.entries(STATUS_LABELS).forEach(([value, label]) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      option.selected = action.status === value;
      select.appendChild(option);
    });
    select.addEventListener('change', () => handleActionStatusChange(action.id, select.value));

    row.appendChild(text);
    row.appendChild(select);
    actionsList.appendChild(row);
  });

  actionsCard.style.display = '';
}

async function handleActionStatusChange(actionId, newStatus) {
  try {
    await updateActionStatus(actionId, newStatus);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    alert("Impossible de mettre à jour le statut de l'action pour le moment.");
  }
}
