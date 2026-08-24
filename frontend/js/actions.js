import { getOpenActions, getActions, updateActionStatus, ApiError } from './api.js';

const actionList = document.getElementById('action-list');
const emptyState = document.getElementById('empty-state');
const errorState = document.getElementById('error-state');
const showCompleted = document.getElementById('show-completed');

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

showCompleted.addEventListener('change', loadActions);

loadActions();

async function loadActions() {
  emptyState.hidden = true;
  errorState.hidden = true;

  try {
    // Coché : toutes les actions (ouvertes + terminées). Décoché : ouvertes uniquement.
    const actions = showCompleted.checked ? await getActions() : await getOpenActions();
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

  actions.forEach((action) => {
    const card = document.createElement('div');
    card.className = 'card session-card';
    card.dataset.actionId = action.id;

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
        <select class="status-select" style="padding:6px 10px; border:1px solid var(--scribe-border); border-radius:8px;">
          <option value="todo" ${action.status === 'todo' ? 'selected' : ''}>À faire</option>
          <option value="in_progress" ${action.status === 'in_progress' ? 'selected' : ''}>En cours</option>
          <option value="done" ${action.status === 'done' ? 'selected' : ''}>Terminé</option>
        </select>
      </div>
    `;

    const select = card.querySelector('.status-select');
    select.addEventListener('change', () => handleStatusChange(action.id, select.value, card));

    actionList.appendChild(card);
  });
}

async function handleStatusChange(actionId, newStatus, cardEl) {
  try {
    await updateActionStatus(actionId, newStatus);

    // En vue "ouvertes uniquement" (case décochée), une action terminée disparaît.
    // En vue "toutes les actions" (case cochée), elle reste affichée avec son nouveau statut.
    if (newStatus === 'done' && !showCompleted.checked) {
      cardEl.remove();
      if (actionList.children.length === 0) {
        emptyState.hidden = false;
      }
    }
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    alert("Impossible de mettre à jour le statut pour le moment.");
  }
}

function escape(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}