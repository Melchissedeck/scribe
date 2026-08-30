// Logique de la page de consentement

import { grantConsent } from './consent.js';
import './theme.js';

const acceptButton = document.getElementById('accept-button');
const refuseButton = document.getElementById('refuse-button');

acceptButton.addEventListener('click', handleAccept);
refuseButton.addEventListener('click', handleRefuse);

function handleAccept() {
  grantConsent();
  window.location.href = 'mode-selection.html';
}

function handleRefuse() {
  window.location.href = 'restricted.html';
}
