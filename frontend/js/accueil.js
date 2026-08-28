import { getMeetings, getActions, getOverdueActions, getDashboardTrends, ApiError } from './api.js';

const meetingGrid = document.getElementById('meeting-grid');
const emptyState = document.getElementById('empty-state');
const errorState = document.getElementById('error-state');

const filterTheme = document.getElementById('filter-theme');
const filterDateFrom = document.getElementById('filter-date-from');
const filterDateTo = document.getElementById('filter-date-to');
const filterReset = document.getElementById('filter-reset');

const filterToggle = document.getElementById('filter-toggle');
const filtersBar = document.getElementById('filters-bar');

filterToggle.addEventListener('click', () => {
  filtersBar.style.display = filtersBar.style.display === 'none' ? 'flex' : 'none';
});

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

let debounceTimer = null;

filterTheme.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadMeetings, 300);
});
filterDateFrom.addEventListener('change', loadMeetings);
filterDateTo.addEventListener('change', loadMeetings);
filterReset.addEventListener('click', () => {
  filterTheme.value = '';
  filterDateFrom.value = '';
  filterDateTo.value = '';
  loadMeetings();
});

loadMeetings();
loadStats();
loadOverdueAlert();
loadTrendChart();

async function loadMeetings() {
  emptyState.hidden = true;
  errorState.hidden = true;

  const filters = {};
  if (filterTheme.value.trim()) filters.theme = filterTheme.value.trim();
  if (filterDateFrom.value) filters.date_from = filterDateFrom.value;
  if (filterDateTo.value) filters.date_to = filterDateTo.value;

  try {
    const meetings = await getMeetings(filters);
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
  meetingGrid.innerHTML = '';

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

async function loadStats() {
  try {
    const [meetings, allActions] = await Promise.all([
      getMeetings(),
      getActions(),
    ]);

    const totalMeetings = meetings.length;
    const summariesCount = meetings.filter((m) => m.summary_excerpt).length;
    const openActions = allActions.filter((a) => a.status === 'todo' || a.status === 'in_progress').length;
    const doneActions = allActions.filter((a) => a.status === 'done').length;
    const totalActions = allActions.length;
    const completionRate = totalActions > 0 ? Math.round((doneActions / totalActions) * 100) : 0;

    const totalMinutes = meetings.reduce((sum, m) => sum + (m.duration_minutes || 0), 0);
    const hoursAnalyzed = (totalMinutes / 60).toFixed(1);

    document.getElementById('stat-total-meetings').textContent = totalMeetings;
    document.getElementById('stat-summaries').textContent = summariesCount;
    document.getElementById('stat-open-actions').textContent = openActions;
    document.getElementById('stat-done-actions').textContent = doneActions;
    document.getElementById('stat-completion-rate').textContent = totalActions > 0 ? `${completionRate}%` : '—';

    document.getElementById('kpi-total-meetings').textContent = totalMeetings;
    document.getElementById('kpi-hours-analyzed').textContent = totalMinutes > 0 ? hoursAnalyzed : '—';
    document.getElementById('kpi-total-actions').textContent = totalActions;

    const summariesCoverage = totalMeetings > 0 ? Math.round((summariesCount / totalMeetings) * 100) : 0;
    document.getElementById('stat-summaries-trend').textContent = totalMeetings > 0 ? `${summariesCoverage}% couverts` : '';
    document.getElementById('stat-done-actions-trend').textContent = totalActions > 0 ? `sur ${totalActions} au total` : '';
    document.getElementById('stat-completion-ratio').textContent = totalActions > 0 ? `${doneActions} / ${totalActions} actions` : '';
    document.getElementById('stat-completion-bar').style.width = `${completionRate}%`;
  } catch (err) {
    // Les stats sont un bonus visuel : en cas d'erreur, on laisse simplement les tirets
    // sans bloquer le reste de la page (filtres et liste des réunions).
    console.error('Impossible de charger les statistiques du dashboard.', err);
  }
}

// ── Alerte actions en retard ─────────────────────────────────────────────
async function loadOverdueAlert() {
  const alertEl = document.getElementById('overdue-alert');
  const titleEl = document.getElementById('overdue-alert-title');
  const listEl = document.getElementById('overdue-list');

  try {
    const overdue = await getOverdueActions();

    if (!overdue || overdue.length === 0) {
      alertEl.hidden = true;
      return;
    }

    titleEl.textContent = `${overdue.length} action${overdue.length > 1 ? 's' : ''} en retard`;

    listEl.innerHTML = '';
    overdue.forEach((action) => {
      const item = document.createElement('li');
      item.className = 'overdue-item';
      item.addEventListener('click', () => {
        window.location.href = `meeting-detail.html?id=${action.meeting_id}`;
      });

      const left = document.createElement('div');
      const desc = document.createElement('div');
      desc.className = 'overdue-item-desc';
      desc.textContent = action.description;
      const meta = document.createElement('div');
      meta.className = 'overdue-item-meta';
      meta.textContent = action.meeting_theme || 'Réunion sans titre';
      left.appendChild(desc);
      left.appendChild(meta);

      const badge = document.createElement('span');
      badge.className = 'overdue-item-badge';
      badge.textContent = formatOverdueBadge(action.due_date);

      item.appendChild(left);
      item.appendChild(badge);
      listEl.appendChild(item);
    });

    alertEl.hidden = false;
  } catch (err) {
    // Non bloquant : si l'appel échoue, on laisse simplement l'alerte masquée
    // plutôt que de casser le reste du dashboard.
    console.error('Impossible de charger les actions en retard.', err);
  }
}

function formatOverdueBadge(dueDateIso) {
  const dueDate = new Date(`${dueDateIso}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((today - dueDate) / (1000 * 60 * 60 * 24));
  if (days <= 0) return 'En retard';
  return `${days} jour${days > 1 ? 's' : ''} de retard`;
}

// ── Graphe de tendance ────────────────────────────────────────────────────
function vizColor(name) {
  return getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(name).trim();
}

async function loadTrendChart() {
  const canvas = document.getElementById('chart-trend');
  const wrap = canvas.closest('.chart-canvas-wrap');
  const emptyEl = document.getElementById('trend-empty');
  const legendEl = document.getElementById('trend-legend');

  try {
    const { points } = await getDashboardTrends('day');

    const hasData = points.some((p) => p.meetings_count > 0 || p.actions_count > 0);
    if (!hasData) {
      wrap.hidden = true;
      emptyEl.hidden = false;
      return;
    }

    const series1 = vizColor('--viz-series-1');
    const series2 = vizColor('--viz-series-2');
    const gridColor = vizColor('--viz-grid');
    const mutedColor = vizColor('--viz-muted');
    const inkColor = vizColor('--viz-ink-2');

    const todayIso = new Date().toISOString().slice(0, 10);
    const currentIndex = points.findIndex((p) => p.period_start === todayIso);
    const labels = points.map((p, i) => formatDayLabel(p.period_start) + (i === currentIndex ? " (aujourd'hui)" : ''));
    const fullLabels = points.map((p, i) => formatDayFull(p.period_start) + (i === currentIndex ? " — aujourd'hui" : ''));
    const pointRadii = points.map((_, i) => (i === currentIndex ? 6 : 4));

    // eslint-disable-next-line no-undef
    new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Réunions',
            data: points.map((p) => p.meetings_count),
            borderColor: series1,
            backgroundColor: series1,
            pointBackgroundColor: series1,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: pointRadii,
            pointHoverRadius: 7,
            borderWidth: 2,
            tension: 0.15,
          },
          {
            label: 'Actions',
            data: points.map((p) => p.actions_count),
            borderColor: series2,
            backgroundColor: series2,
            pointBackgroundColor: series2,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: pointRadii,
            pointHoverRadius: 7,
            borderWidth: 2,
            tension: 0.15,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0b0b0b',
            padding: 10,
            cornerRadius: 6,
            callbacks: {
              title: (items) => fullLabels[items[0].dataIndex],
              label: (ctx) => `${ctx.parsed.y} · ${ctx.dataset.label}`,
            },
          },
        },
        scales: {
          x: {
            ticks: {
              color: (ctx) => (ctx.index === currentIndex ? inkColor : mutedColor),
              font: (ctx) => ({ size: 11, weight: ctx.index === currentIndex ? '700' : '400' }),
            },
            grid: { display: false },
            border: { display: false },
          },
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: mutedColor, font: { size: 11 } },
            grid: { color: gridColor },
            border: { display: false },
          },
        },
      },
    });

    legendEl.innerHTML = '';
    [['Réunions', series1], ['Actions', series2]].forEach(([label, color]) => {
      const item = document.createElement('span');
      item.className = 'chart-legend-item';
      const swatch = document.createElement('span');
      swatch.className = 'chart-legend-swatch';
      swatch.style.background = color;
      const text = document.createElement('span');
      text.textContent = label;
      item.appendChild(swatch);
      item.appendChild(text);
      legendEl.appendChild(item);
    });
  } catch (err) {
    console.error('Impossible de charger la tendance du dashboard.', err);
    wrap.hidden = true;
    emptyEl.hidden = false;
  }
}

function formatDayLabel(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  return date.toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit' });
}

function formatDayFull(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  const label = date.toLocaleDateString('fr-FR', { weekday: 'long', day: '2-digit', month: 'long' });
  return label.charAt(0).toUpperCase() + label.slice(1);
}