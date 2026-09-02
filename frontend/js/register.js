// Logique de la page d'inscription

import { registerUser, ApiError } from './api.js';
import './theme.js';
import { initPasswordToggles } from './password-toggle.js';

const form = document.getElementById('register-form');
const errorMessage = document.getElementById('error-message');
const submitButton = document.getElementById('submit-button');

form.addEventListener('submit', handleSubmit);
initPasswordToggles();

async function handleSubmit(event) {
  event.preventDefault();
  errorMessage.textContent = '';

  const name = document.getElementById('name').value;
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  submitButton.disabled = true;
  submitButton.textContent = 'Creation en cours...';

  try {
    await registerUser(name, email, password);
    window.location.href = 'login.html';
  } catch (error) {
    if (error instanceof ApiError) {
      errorMessage.textContent = error.message;
    } else {
      errorMessage.textContent = 'Impossible de contacter le serveur';
    }
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Creer mon compte';
  }
}
