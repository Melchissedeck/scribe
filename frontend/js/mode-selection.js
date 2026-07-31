// Logique de la page de choix du mode de captation

import { requireConsent } from './consent.js';

requireConsent();

const visioOption = document.getElementById('visio-option');
const dictaOption = document.getElementById('dicta-option');

visioOption.addEventListener('click', () => {
  window.location.href = 'visio.html';
});

dictaOption.addEventListener('click', () => {
  window.location.href = 'dicta.html';
});
