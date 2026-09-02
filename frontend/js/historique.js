import { getMeetings, deleteMeeting, ApiError } from './api.js';
import { confirmModal } from './modal.js';
import './sidebar.js';
import './theme.js';

const meetingGrid  = document.getElementById('meeting-grid');
const emptyState   = document.getElementById('empty-state');
const errorState   = document.getElementById('error-state');
const resultsCount = document.getElementById('results-count');
const paginationEl = document.getElementById('pagination');

const searchInput  = document.getElementById('filter-search');
const dateSelect   = document.getElementById('filter-date');
const themeInput   = document.getElementById('filter-theme');
const statusSelect = document.getElementById('filter-status');

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

const PAGE_SIZE = 9;
let currentPage = 1;
let allMeetings = [];
let filteredMeetings = [];

const activeFilters = { search: '', date: '', theme: '', status: '' };

// ── Chargement initial ────────────────────────────────────────────────────────

loadMeetings();

async function loadMeetings() {
  try {
    allMeetings = await getMeetings();
    applyFilters();
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    errorState.hidden = false;
  }
}

// ── Événements filtres ────────────────────────────────────────────────────────

let searchDebounce = null;
searchInput.addEventListener('input', () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    activeFilters.search = searchInput.value.trim().toLowerCase();
    applyFilters();
  }, 200);
});

dateSelect.addEventListener('change', () => {
  activeFilters.date = dateSelect.value;
  applyFilters();
});

let themeDebounce = null;
themeInput.addEventListener('input', () => {
  clearTimeout(themeDebounce);
  themeDebounce = setTimeout(() => {
    activeFilters.theme = themeInput.value.trim().toLowerCase();
    applyFilters();
  }, 200);
});

statusSelect.addEventListener('change', () => {
  activeFilters.status = statusSelect.value;
  applyFilters();
});


// ── Filtrage ──────────────────────────────────────────────────────────────────

function applyFilters() {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const weekStart = new Date(todayStart);
  const day = weekStart.getDay();
  weekStart.setDate(weekStart.getDate() - (day === 0 ? 6 : day - 1));

  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

  const filtered = allMeetings.filter((m) => {
    if (activeFilters.search) {
      const title = (m.theme || '').toLowerCase();
      if (!title.includes(activeFilters.search)) return false;
    }

    if (activeFilters.date) {
      const mDate = new Date(m.date.endsWith('Z') || m.date.includes('+') ? m.date : m.date + 'Z');
      if (activeFilters.date === 'today' && mDate < todayStart) return false;
      if (activeFilters.date === 'week'  && mDate < weekStart)  return false;
      if (activeFilters.date === 'month' && mDate < monthStart) return false;
    }

    if (activeFilters.theme) {
      const theme = (m.theme || '').toLowerCase();
      if (!theme.includes(activeFilters.theme)) return false;
    }

    if (activeFilters.status && m.summary_status !== activeFilters.status) return false;

    return true;
  });

  filteredMeetings = filtered;
  currentPage = 1;
  renderPage();
}

function renderPage() {
  const start = (currentPage - 1) * PAGE_SIZE;
  renderMeetings(filteredMeetings.slice(start, start + PAGE_SIZE));
  renderPagination();
}

function renderPagination() {
  paginationEl.innerHTML = '';
  const totalPages = Math.ceil(filteredMeetings.length / PAGE_SIZE);
  if (totalPages <= 1) return;

  paginationEl.innerHTML = `
    <button class="pagination-btn" id="pg-prev" ${currentPage === 1 ? 'disabled' : ''}>
      &#8592; Précédent
    </button>
    <span class="pagination-info">Page ${currentPage} / ${totalPages}</span>
    <button class="pagination-btn" id="pg-next" ${currentPage === totalPages ? 'disabled' : ''}>
      Suivant &#8594;
    </button>
  `;
  document.getElementById('pg-prev').addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; renderPage(); window.scrollTo(0, 0); }
  });
  document.getElementById('pg-next').addEventListener('click', () => {
    if (currentPage < totalPages) { currentPage++; renderPage(); window.scrollTo(0, 0); }
  });
}

// ── Rendu ─────────────────────────────────────────────────────────────────────

function renderMeetings(meetings) {
  meetingGrid.innerHTML = '';
  emptyState.hidden = true;
  errorState.hidden = true;

  const hasActiveFilter = activeFilters.search || activeFilters.date || activeFilters.theme || activeFilters.status;

  if (hasActiveFilter) {
    const total = filteredMeetings.length;
    resultsCount.textContent = `${total} résultat${total !== 1 ? 's' : ''}`;
    resultsCount.hidden = false;
  } else {
    resultsCount.hidden = true;
  }

  if (filteredMeetings.length === 0) {
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
          <div class="session-title">${escapeHtml(meeting.theme || 'Réunion sans titre')}</div>
          <div class="session-date">${formatDate(meeting.date)}</div>
        </div>
        <button class="session-delete-btn" title="Supprimer cette réunion" aria-label="Supprimer">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        </button>
      </div>
      <p class="session-desc">${escapeHtml(meeting.summary_excerpt || 'Compte-rendu non encore disponible.')}</p>
      <div class="session-footer">
        ${meetingTypeBadge(meeting.meeting_type)}
        <button class="ghost-btn">Voir le compte-rendu</button>
      </div>
    `;

    card.querySelector('.ghost-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      window.location.href = `meeting-detail.html?id=${meeting.id}`;
    });

    card.querySelector('.session-delete-btn').addEventListener('click', async (e) => {
      e.stopPropagation();
      const title = escapeHtml(meeting.theme || 'Réunion sans titre');
      const ok = await confirmModal({
        title: `Supprimer "${title}" ?`,
        message: 'La réunion, sa transcription et toutes ses actions seront définitivement supprimées. Cette action est irréversible.',
        confirmLabel: 'Supprimer',
      });
      if (!ok) return;
      try {
        await deleteMeeting(meeting.id);
        allMeetings = allMeetings.filter((m) => m.id !== meeting.id);
        applyFilters();
      } catch {
        alert('Impossible de supprimer la réunion. Réessayez.');
      }
    });

    meetingGrid.appendChild(card);
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(isoString) {
  const utc = isoString.endsWith('Z') || isoString.includes('+') ? isoString : isoString + 'Z';
  return new Date(utc).toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function meetingTypeBadge(type) {
  if (type === 'in_person') {
    return '<span class="meeting-type-badge meeting-type-badge--in-person"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>Présentiel</span>';
  }
  if (type === 'remote') {
    return '<span class="meeting-type-badge meeting-type-badge--remote"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>À distance</span>';
  }
  return '';
}
