// Gere l'etat du consentement RGPD avant toute captation

const CONSENT_KEY = 'consent_accepted';

export function hasConsent() {
  // Verifie si l'utilisateur a deja valide le consentement pour cette session
  return sessionStorage.getItem(CONSENT_KEY) === 'true';
}

export function grantConsent() {
  // Enregistre que l'utilisateur a valide le consentement
  sessionStorage.setItem(CONSENT_KEY, 'true');
}

export function requireConsent() {
  // Redirige vers l'ecran de consentement si celui-ci n'a pas ete valide
  if (!hasConsent()) {
    window.location.href = 'consent.html';
  }
}
