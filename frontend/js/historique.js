import { getMeetings, ApiError } from './api.js';
import './sidebar.js';
import './theme.js';

const meetingGrid  = document.getElementById('meeting-grid');
const emptyState   = document.getElementById('empty-state');
const errorState   = document.getElementById('error-state');
const resultsCount = document.getElementById('results-count');
const paginationEl = document.getElementById('pagination');

const searchInput  = document.getElementById('filter-search');
const dateSelect   = document.getElementById('filter-date');
const pillButtons  = document.querySelectorAll('.hist-pill');

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

const activeFilters = { search: '', date: '', status: '' };

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

pillButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    pillButtons.forEach((b) => b.classList.remove('hist-pill--active'));
    btn.classList.add('hist-pill--active');
    activeFilters.status = btn.dataset.status;
    applyFilters();
  });
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

    if (activeFilters.status && m.status !== activeFilters.status) return false;

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

  const hasActiveFilter = activeFilters.search || activeFilters.date || activeFilters.status;

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
      </div>
      <p class="session-desc">${escapeHtml(meeting.summary_excerpt || 'Compte-rendu non encore disponible.')}</p>
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
