import { getMeetingSummary, getDiarizedTranscript, ApiError } from './api.js';

const themeEl = document.getElementById('meeting-theme');
const dateEl = document.getElementById('meeting-date');
const summaryEl = document.getElementById('meeting-summary');
const speakersCard = document.getElementById('speakers-card');
const speakersTranscript = document.getElementById('speakers-transcript');

const SPEAKER_COLORS = [
  { bg: '#EAF1FF', text: '#2563EB' },
  { bg: '#FEF3C7', text: '#92400E' },
  { bg: '#DCFCE7', text: '#166534' },
  { bg: '#FCE7F3', text: '#9D174D' },
  { bg: '#EDE9FE', text: '#5B21B6' },
  { bg: '#FFEDD5', text: '#9A3412' },
];

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

  await Promise.all([
    loadSummary(meetingId),
    loadSpeakers(meetingId),
  ]);
}

async function loadSummary(meetingId) {
  try {
    const result = await getMeetingSummary(meetingId);
    themeEl.textContent = 'Compte-rendu';
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
    summaryEl.textContent = 'Impossible de charger le compte-rendu pour le moment.';
  }
}

async function loadSpeakers(meetingId) {
  try {
    const result = await getDiarizedTranscript(meetingId);
    if (!result.segments || result.segments.length === 0) return;
    renderSpeakers(result.segments);
  } catch (error) {
    // 404 = pas de diarisation, on n'affiche rien (cas normal pour réunions sans segments)
    if (error instanceof ApiError && error.status === 404) return;
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return;
    // Erreur inattendue : on affiche un message discret
    speakersCard.style.display = '';
    speakersTranscript.textContent = 'Impossible de charger les intervenants.';
  }
}

function renderSpeakers(segments) {
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
