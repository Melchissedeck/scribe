// Hamburger sidebar — auto-initializes on import for all dash-shell pages
const sidebar = document.querySelector('.dash-sidebar');
if (sidebar) {
  const hamburger = document.createElement('button');
  hamburger.className = 'dash-hamburger';
  hamburger.type = 'button';
  hamburger.setAttribute('aria-label', 'Ouvrir le menu');
  hamburger.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;

  const overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);

  const header = document.querySelector('.dash-header');
  if (header) header.insertAdjacentElement('afterbegin', hamburger);

  const open = () => {
    sidebar.classList.add('dash-sidebar--open');
    overlay.classList.add('sidebar-overlay--visible');
    hamburger.setAttribute('aria-label', 'Fermer le menu');
  };

  const close = () => {
    sidebar.classList.remove('dash-sidebar--open');
    overlay.classList.remove('sidebar-overlay--visible');
    hamburger.setAttribute('aria-label', 'Ouvrir le menu');
  };

  hamburger.addEventListener('click', () => {
    sidebar.classList.contains('dash-sidebar--open') ? close() : open();
  });

  overlay.addEventListener('click', close);

  sidebar.querySelectorAll('a.dash-nav-item').forEach(link => {
    link.addEventListener('click', () => { if (window.innerWidth <= 768) close(); });
  });
}
