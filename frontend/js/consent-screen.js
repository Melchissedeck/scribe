// Logique de la page de consentement

import { grantConsent } from './consent.js';
import { recordConsent } from './api.js';
import './theme.js';

const acceptButton = document.getElementById('accept-button');
const refuseButton = document.getElementById('refuse-button');

acceptButton.addEventListener('click', handleAccept);
refuseButton.addEventListener('click', handleRefuse);

async function handleAccept() {
  grantConsent();

  // Enregistre le consentement côté serveur : c'est cet appel, vérifié
  // par le backend avant toute captation, qui rend le consentement
  // effectif plutôt que purement déclaratif côté client. Un échec réseau
  // ne doit pas bloquer la navigation : la captation elle-même échouera
  // proprement (403) si le consentement n'a pas pu être enregistré.
  try {
    await recordConsent();
  } catch (error) {
    console.warn("Impossible d'enregistrer le consentement côté serveur.", error);
  }

  window.location.href = 'mode-selection.html';
}

function handleRefuse() {
  window.location.href = 'restricted.html';
}
