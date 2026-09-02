import { deleteAccount, ApiError } from './api.js';
import { confirmModal } from './modal.js';
import './sidebar.js';
import './theme.js';

if (!sessionStorage.getItem('access_token')) {
  window.location.href = 'login.html';
}

document.getElementById('logout-btn').addEventListener('click', () => {
  sessionStorage.removeItem('access_token');
  window.location.href = 'login.html';
});

const deleteButton = document.getElementById('delete-account-btn');
const deleteError = document.getElementById('delete-account-error');

deleteButton.addEventListener('click', async () => {
  deleteError.textContent = '';

  const confirmed = await confirmModal({
    title: 'Supprimer votre compte ?',
    message: 'Toutes vos réunions, transcriptions et actions seront définitivement perdues. Cette action est irréversible.',
    confirmLabel: 'Supprimer le compte',
  });

  if (!confirmed) {
    return;
  }

  deleteButton.disabled = true;
  deleteButton.textContent = 'Suppression...';

  try {
    await deleteAccount();
    sessionStorage.removeItem('access_token');
    window.location.href = 'register.html';
  } catch (error) {
    deleteButton.disabled = false;
    deleteButton.textContent = 'Supprimer mon compte';

    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      window.location.href = 'login.html';
      return;
    }

    deleteError.textContent = 'Impossible de supprimer le compte pour le moment.';
  }
});
