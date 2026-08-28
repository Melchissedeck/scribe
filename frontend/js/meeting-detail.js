import {
  getMeetingDetails, getSpeakingTime, generateSummary, extractActions,
  updateMeetingTheme, updateActionStatus, exportMeetingPdf, ApiError,
} from './api.js';

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

const SPEAKER_COLORS = [
  { bg: '#EAF1FF', text: '#2563EB', bar: '#3B82F6' },
  { bg: '#FEF3C7', text: '#92400E', bar: '#F59E0B' },
  { bg: '#DCFCE7', text: '#166534', bar: '#22C55E' },
  { bg: '#FCE7F3', text: '#9D174D', bar: '#EC4899' },
  { bg: '#EDE9FE', text: '#5B21B6', bar: '#8B5CF6' },
  { bg: '#FFEDD5', text: '#9A3412', bar: '#F97316' },
];

const STATUS_LABELS = {
  todo: 'À faire',
  in_progress: 'En cours',
  done: 'Terminé',
};

const titleEl         = document.getElementById('cr-title');
const metaEl          = document.getElementById('cr-meta');
const summaryEl       = document.getElementById('cr-summary');
const speakersBadge   = document.getElementById('cr-speakers-badge');
const speakingTimeEl  = document.getElementById('cr-speaking-time');
const segmentsEl      = document.getElementById('cr-segments');
const actionsCard     = document.getElementById('cr-actions-card');
const actionsBody     = document.getElementById('cr-actions-body');

let currentMeetingId = null;
let currentTheme = null;

loadData();

async function loadData() {
  const meetingId = new URLSearchParams(window.location.search).get('id');
  currentMeetingId = meetingId;
  if (!meetingId) {
    summaryEl.textContent = 'Aucune réunion sélectionnée.';
    return;
  }

  try {
    const [details, speakingTime] = await Promise.allSettled([
      getMeetingDetails(meetingId),
      getSpeakingTime(meetingId),
    ]);

    if (details.status === 'rejected') {
      const err = details.reason;
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        window.location.href = 'login.html';
        return;
      }
      summaryEl.textContent = 'Impossible de charger cette réunion.';
      return;
    }

    const d = details.value;
    const st = speakingTime.status === 'fulfilled' ? speakingTime.value : null;

    renderMeta(d);
    await renderSummary(d);
    renderExchanges(d.segments, st, d.started_at);

    const actions = await ensureActionsAndTheme(d);
    renderActions(actions);
  } catch (err) {
    summaryEl.textContent = 'Impossible de charger cette réunion.';
  }
}

// Si aucune action n'a encore été extraite, on lance l'extraction LLM
// (thème + actions) une seule fois. On ne la relance pas si des actions
// existent déjà, pour ne pas créer de doublons à chaque ouverture de page.
async function ensureActionsAndTheme(details) {
  if (details.actions && details.actions.length > 0) {
    return details.actions;
  }
  try {
    const result = await extractActions(details.id);
    if (result.theme && !currentTheme) {
      currentTheme = result.theme;
      titleEl.textContent = currentTheme;
    }
    return result.actions;
  } catch (err) {
    return details.actions;
  }
}

function renderMeta(details) {
  currentTheme = details.theme || null;
  titleEl.textContent = currentTheme || 'Réunion sans titre';
  const date = new Date(details.started_at).toLocaleString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  let duration = '';
  if (details.stopped_at) {
    const secs = Math.round((new Date(details.stopped_at) - new Date(details.started_at)) / 1000);
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    duration = h > 0 ? ` · ${h}h${String(m).padStart(2, '0')}` : ` · ${m} min`;
  }

  const participants = details.speakers?.length ?? 0;
  const participantsTxt = participants > 0 ? ` · ${participants} participant${participants > 1 ? 's' : ''}` : '';

  metaEl.textContent = `${date}${duration}${participantsTxt}`;
}

function renderMarkdown(el, text) {
  el.innerHTML = window.marked ? window.marked.parse(text) : text.replace(/\n/g, '<br>');
}

async function renderSummary(details) {
  if (details.summary && details.summary.trim()) {
    renderMarkdown(summaryEl, details.summary);
    return;
  }
  summaryEl.textContent = 'Génération du résumé en cours…';
  try {
    const result = await generateSummary(details.id);
    renderMarkdown(summaryEl, result.summary);
  } catch (err) {
    if (err instanceof ApiError && err.status === 400) {
      summaryEl.textContent = 'Aucune transcription disponible pour générer un résumé.';
    } else {
      summaryEl.textContent = 'Impossible de générer le résumé pour le moment.';
    }
  }
}

function renderExchanges(segments, speakingTime, startedAt) {
  const speakerColorMap = buildColorMap(segments);
  const speakerCount = Object.keys(speakerColorMap).length;

  speakersBadge.textContent = `Diarisation · ${speakerCount} locuteur${speakerCount > 1 ? 's' : ''}`;

  if (speakingTime?.entries?.length > 0) {
    renderSpeakingTime(speakingTime.entries, speakerColorMap);
  }

  if (!segments || segments.length === 0) {
    segmentsEl.innerHTML = '<p style="color:var(--color-text-muted);font-size:13px;">Aucun échange capturé.</p>';
    return;
  }

  segmentsEl.innerHTML = segments.map((seg, i) => {
    const colors = speakerColorMap[seg.speaker_name] ?? SPEAKER_COLORS[0];
    const initials = getInitials(seg.speaker_name);
    const timestamp = seg.start != null ? formatRelativeTime(seg.start, startedAt) : null;
    const speakerIndex = Object.keys(speakerColorMap).indexOf(seg.speaker_name) + 1;

    return `
      <div class="cr-segment">
        <div class="cr-avatar" style="background:${colors.bg};color:${colors.text};">${initials}</div>
        <div class="cr-segment-body">
          <div class="cr-segment-header">
            <span class="cr-segment-name">${seg.speaker_name}</span>
            <span class="cr-segment-badge" style="background:${colors.bg};color:${colors.text};">Locuteur ${speakerIndex}</span>
            ${timestamp ? `<span class="cr-segment-time">${timestamp}</span>` : ''}
          </div>
          <p class="cr-segment-text">« ${seg.text} »</p>
        </div>
      </div>`;
  }).join('');
}

function renderSpeakingTime(entries, colorMap) {
  speakingTimeEl.innerHTML = entries.map((e) => {
    const colors = colorMap[e.speaker] ?? SPEAKER_COLORS[0];
    const mins = Math.floor(e.seconds / 60);
    const secs = Math.round(e.seconds % 60);
    const label = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    return `
      <div class="cr-st-entry">
        <div class="cr-st-meta">
          <span class="cr-st-name">${e.speaker}</span>
          <span class="cr-st-value">${label} · ${e.percentage}%</span>
        </div>
        <div class="cr-st-track">
          <div class="cr-st-bar" style="width:${e.percentage}%;background:${colors.bar};"></div>
        </div>
      </div>`;
  }).join('');
}

function renderActions(actions) {
  if (!actions || actions.length === 0) return;

  actionsBody.innerHTML = actions.map((action) => `
    <tr>
      <td>${action.description}</td>
      <td>
        <select data-id="${action.id}">
          ${Object.entries(STATUS_LABELS).map(([val, label]) =>
            `<option value="${val}"${action.status === val ? ' selected' : ''}>${label}</option>`
          ).join('')}
        </select>
      </td>
    </tr>
  `).join('');

  actionsBody.querySelectorAll('select').forEach((sel) => {
    sel.addEventListener('change', () => updateActionStatus(sel.dataset.id, sel.value).catch(() => {
      alert("Impossible de mettre à jour le statut.");
    }));
  });

  actionsCard.style.display = '';
}

// ── Titre éditable ────────────────────────────────────────────────────────
// N'enregistre que si l'utilisateur a réellement tapé quelque chose : un
// blur seul (clic ailleurs sur la page pendant que le texte de repli
// "Réunion sans titre" est affiché) ne doit jamais être pris pour un
// renommage volontaire.
let titleEditedByUser = false;

titleEl.addEventListener('input', () => {
  titleEditedByUser = true;
});

titleEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    titleEl.blur();
  }
});

titleEl.addEventListener('blur', async () => {
  if (!titleEditedByUser) return;
  titleEditedByUser = false;

  const newTheme = titleEl.textContent.trim();
  if (newTheme === (currentTheme || '')) return;

  try {
    const result = await updateMeetingTheme(currentMeetingId, newTheme || null);
    currentTheme = result.theme;
    titleEl.textContent = currentTheme || 'Réunion sans titre';
  } catch (err) {
    titleEl.textContent = currentTheme || 'Réunion sans titre';
  }
});

// ── Action buttons ────────────────────────────────────────────────────────
async function downloadPdf(button) {
  const orig = button.textContent;
  button.disabled = true;
  button.textContent = 'Génération…';

  try {
    const { blob, filename } = await exportMeetingPdf(currentMeetingId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err instanceof ApiError ? err.message : 'Impossible de générer le PDF pour le moment.');
  } finally {
    button.disabled = false;
    button.textContent = orig;
  }
}

document.getElementById('btn-pdf').addEventListener('click', (e) => downloadPdf(e.currentTarget));

document.getElementById('btn-word').addEventListener('click', () => {
  alert('Export Word bientôt disponible.');
});

document.getElementById('btn-copy').addEventListener('click', () => {
  const text = summaryEl.innerText;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('btn-copy');
    const orig = btn.textContent;
    btn.textContent = 'Copié !';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
});

document.getElementById('btn-fab').addEventListener('click', (e) => downloadPdf(e.currentTarget));

// ── Helpers ───────────────────────────────────────────────────────────────
function buildColorMap(segments) {
  const map = {};
  let i = 0;
  (segments ?? []).forEach((seg) => {
    if (!(seg.speaker_name in map)) {
      map[seg.speaker_name] = SPEAKER_COLORS[i % SPEAKER_COLORS.length];
      i++;
    }
  });
  return map;
}

function getInitials(name) {
  return name.split(' ').map((w) => w[0] ?? '').join('').toUpperCase().slice(0, 2) || '?';
}

function formatRelativeTime(unixSeconds, startedAt) {
  const startUnix = new Date(startedAt).getTime() / 1000;
  const relative = Math.max(0, unixSeconds - startUnix);
  const m = Math.floor(relative / 60);
  const s = Math.floor(relative % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
