import { getActions, updateActionStatus, updateActionDueDate, ApiError } from './api.js';

const today = new Date().toISOString().split('T')[0];

const emptyState = document.getElementById('empty-state');
const errorState = document.getElementById('error-state');

const lists = {
  todo: document.getElementById('list-todo'),
  in_progress: document.getElementById('list-in_progress'),
  done: document.getElementById('list-done'),
};
const counts = {
  todo: document.getElementById('count-todo'),
  in_progress: document.getElementById('count-in_progress'),
  done: document.getElementById('count-done'),
};

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

const colStatus = new Map([
  [lists.todo, 'todo'],
  [lists.in_progress, 'in_progress'],
  [lists.done, 'done'],
]);

initSortable();
loadActions();

function initSortable() {
  Object.values(lists).forEach((colEl) => {
    Sortable.create(colEl, {
      group: 'kanban-actions',
      animation: 150,
      ghostClass: 'kanban-card--ghost',
      dragClass: 'kanban-card--dragging',
      handle: '.kanban-drag-handle',
      onEnd(evt) {
        const cardEl = evt.item;
        const newColEl = evt.to;
        const oldColEl = evt.from;

        if (newColEl === oldColEl) return;

        const newStatus = colStatus.get(newColEl);
        const oldStatus = cardEl.dataset.status;
        const actionId = cardEl.dataset.actionId;

        cardEl.dataset.status = newStatus;
        const select = cardEl.querySelector('.kanban-status-select');
        if (select) select.value = newStatus;
        refreshOverdueState(cardEl);
        updateCounts();

        updateActionStatus(actionId, newStatus).catch((err) => {
          oldColEl.insertBefore(cardEl, oldColEl.children[evt.oldIndex] ?? null);
          cardEl.dataset.status = oldStatus;
          if (select) select.value = oldStatus;
          refreshOverdueState(cardEl);
          updateCounts();
          if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
            window.location.href = 'login.html';
            return;
          }
          alert('Impossible de déplacer cette action.');
        });
      },
    });
  });
}

async function loadActions() {
  emptyState.hidden = true;
  errorState.hidden = true;
  Object.values(lists).forEach((l) => { l.innerHTML = ''; });

  try {
    const actions = await getActions();
    renderActions(actions);
  } catch (err) {
    console.error('loadActions error:', err);
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    errorState.hidden = false;
  }
}

function renderActions(actions) {
  if (actions.length === 0) {
    emptyState.hidden = false;
    updateCounts();
    return;
  }

  actions.forEach((action) => {
    const col = lists[action.status] ?? lists.todo;
    col.appendChild(buildCard(action));
  });

  updateCounts();
}

function buildCard(action) {
  const card = document.createElement('div');
  card.className = 'kanban-card';
  card.dataset.status = action.status;
  card.dataset.dueDate = action.due_date ?? '';
  card.dataset.actionId = action.id;

  const overdue = action.due_date && action.due_date < today && action.status !== 'done';
  if (overdue) card.classList.add('kanban-card--overdue');

  card.innerHTML = `
    <div class="kanban-drag-handle" title="Déplacer">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/></svg>
    </div>
    <p class="kanban-card-desc">${escapeHtml(action.description)}</p>
    <div class="kanban-card-footer">
      <div class="kanban-date-wrap">
        <div class="kanban-date-label-row">
          <label class="kanban-date-label">Échéance</label>
          <span class="kanban-overdue-badge"${overdue ? '' : ' hidden'}>En retard</span>
        </div>
        <input type="date" class="kanban-date-input${overdue ? ' kanban-date-input--overdue' : ''}" value="${action.due_date ?? ''}" min="${today}">
      </div>
      <select class="kanban-status-select">
        <option value="todo" ${action.status === 'todo' ? 'selected' : ''}>À faire</option>
        <option value="in_progress" ${action.status === 'in_progress' ? 'selected' : ''}>En cours</option>
        <option value="done" ${action.status === 'done' ? 'selected' : ''}>Terminé</option>
      </select>
    </div>
  `;

  const select = card.querySelector('.kanban-status-select');
  select.addEventListener('change', () => handleStatusChange(action.id, select.value, card));

  const dateInput = card.querySelector('.kanban-date-input');
  dateInput.addEventListener('change', () => handleDueDateChange(action.id, dateInput.value, dateInput));

  return card;
}

function refreshOverdueState(cardEl) {
  const overdue = cardEl.dataset.dueDate
    && cardEl.dataset.dueDate < today
    && cardEl.dataset.status !== 'done';

  cardEl.classList.toggle('kanban-card--overdue', Boolean(overdue));

  const badge = cardEl.querySelector('.kanban-overdue-badge');
  if (badge) badge.hidden = !overdue;

  const dateInput = cardEl.querySelector('.kanban-date-input');
  if (dateInput) dateInput.classList.toggle('kanban-date-input--overdue', Boolean(overdue));
}

async function handleStatusChange(actionId, newStatus, cardEl) {
  const oldStatus = cardEl.dataset.status;
  try {
    await updateActionStatus(actionId, newStatus);

    cardEl.dataset.status = newStatus;
    lists[newStatus].appendChild(cardEl);
    refreshOverdueState(cardEl);

    const totalVisible = document.querySelectorAll('.kanban-card').length;
    emptyState.hidden = totalVisible > 0;

    updateCounts();
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    cardEl.querySelector('.kanban-status-select').value = oldStatus;
    alert('Impossible de mettre à jour le statut pour le moment.');
  }
}

async function handleDueDateChange(actionId, newDate, inputEl) {
  const prevDate = inputEl.dataset.prev ?? '';
  inputEl.dataset.prev = newDate;
  try {
    await updateActionDueDate(actionId, newDate);
    const cardEl = inputEl.closest('.kanban-card');
    if (cardEl) {
      cardEl.dataset.dueDate = newDate;
      refreshOverdueState(cardEl);
    }
  } catch (err) {
    inputEl.value = prevDate;
    inputEl.dataset.prev = prevDate;
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      window.location.href = 'login.html';
      return;
    }
    alert("Impossible de mettre à jour l'échéance.");
  }
}

function updateCounts() {
  Object.entries(lists).forEach(([status, list]) => {
    counts[status].textContent = list.children.length;
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
