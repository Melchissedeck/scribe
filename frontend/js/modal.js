// Modale de confirmation réutilisable — remplace window.confirm()
// Usage : const ok = await confirmModal({ title, message, confirmLabel });

export function confirmModal({
  title,
  message,
  confirmLabel = 'Confirmer',
  danger = true,
}) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');

    const btnClass = danger ? 'modal-btn--danger' : 'modal-btn--primary';

    overlay.innerHTML = `
      <div class="modal-card">
        <h3 class="modal-title">${title}</h3>
        <p class="modal-message">${message}</p>
        <div class="modal-actions">
          <button class="modal-btn modal-btn--cancel">Annuler</button>
          <button class="modal-btn ${btnClass}">${confirmLabel}</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';

    const close = (result) => {
      overlay.remove();
      document.body.style.overflow = '';
      resolve(result);
    };

    overlay.querySelector('.modal-btn--cancel').addEventListener('click', () => close(false));
    overlay.querySelector(`.${btnClass}`).addEventListener('click', () => close(true));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(false); });

    const keyHandler = (e) => {
      if (e.key === 'Escape') { document.removeEventListener('keydown', keyHandler); close(false); }
    };
    document.addEventListener('keydown', keyHandler);
  });
}
