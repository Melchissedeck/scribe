// theme.js — bascule sombre/clair, auto-initialise à l'import

// Synchronise la préférence sauvegardée (complète le script inline anti-FOUC)
const saved = localStorage.getItem('scribe-theme');
if (saved) {
  document.documentElement.setAttribute('data-theme', saved);
} else if (!document.documentElement.hasAttribute('data-theme')
           && window.matchMedia('(prefers-color-scheme: dark)').matches) {
  document.documentElement.setAttribute('data-theme', 'dark');
}

const sunIcon  = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`;
const moonIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

const btn = document.createElement('button');
btn.className = 'theme-toggle';
btn.type = 'button';

function updateBtn() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  btn.innerHTML = dark ? sunIcon : moonIcon;
  btn.title = dark ? 'Mode clair' : 'Mode sombre';
  btn.setAttribute('aria-label', btn.title);
}

updateBtn();

const headerActions = document.querySelector('.dash-header-actions');
if (headerActions) {
  headerActions.insertBefore(btn, headerActions.firstChild);
} else {
  Object.assign(btn.style, { position: 'fixed', top: '16px', right: '16px', zIndex: '500' });
  document.body.appendChild(btn);
}

btn.addEventListener('click', () => {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  const next = dark ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('scribe-theme', next);
  updateBtn();
});
