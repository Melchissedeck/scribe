// Logique de la page de connexion

import { loginUser, ApiError } from './api.js';

const form = document.getElementById('login-form');
const errorMessage = document.getElementById('error-message');
const submitButton = document.getElementById('submit-button');

form.addEventListener('submit', handleSubmit);

async function handleSubmit(event) {
  event.preventDefault();
  errorMessage.textContent = '';

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  submitButton.disabled = true;
  submitButton.textContent = 'Connexion en cours...';

  try {
    const result = await loginUser(email, password);
    sessionStorage.setItem('access_token', result.access_token);
    window.location.href = 'dashboard.html';
  } catch (error) {
    if (error instanceof ApiError) {
      errorMessage.textContent = error.message;
    } else {
      errorMessage.textContent = 'Impossible de contacter le serveur';
    }
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Se connecter';
  }
}
