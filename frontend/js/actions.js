import { getActions, ApiError } from './api.js';

const actionList = document.getElementById('action-list');
const emptyState = document.getElementById('empty-state');
const errorState = document.getElementById('error-state');
const filterStatus = document.getElementById('filter-status');

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

filterStatus.addEventListener('change', loadActions);

loadActions();

async function loadActions() {
  emptyState.hidden = true;
  errorState.hidden = true;

  try {
    const status = filterStatus.value || null;
    const actions = await getActions(status);
    renderActions(actions);
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    errorState.hidden = false;
  }
}

function renderActions(actions) {
  actionList.innerHTML = '';

  if (actions.length === 0) {
    emptyState.hidden = false;
    return;
  }

  const statusLabels = {
    todo: 'À faire',
    in_progress: 'En cours',
    done: 'Terminé',
  };
  const statusBadges = {
    todo: 'badge-active',
    in_progress: 'badge-active',
    done: 'badge-done',
  };

  actions.forEach((action) => {
    const card = document.createElement('div');
    card.className = 'card session-card';

    card.innerHTML = `
      <div class="session-top">
        <div class="session-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>
          </svg>
        </div>
        <div style="flex:1;min-width:0;">
          <div class="session-title">${escape(action.description)}</div>
          <div class="session-date">${action.due_date ? 'Échéance : ' + action.due_date : 'Sans échéance'}</div>
        </div>
        <span class="badge ${statusBadges[action.status] || 'badge-active'}">${statusLabels[action.status] || action.status}</span>
      </div>
    `;

    actionList.appendChild(card);
  });
}

function escape(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}