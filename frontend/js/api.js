// Module centralisant les appels vers l'API backend

const API_BASE_URL = 'http://127.0.0.1:8000';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function getAuthHeaders() {
  // Ajoute le token JWT stocke en session, si present
  const token = sessionStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiRequest(path, options = {}) {
  // Effectue une requete vers l'API et normalise la gestion des erreurs
  const response = await fetch(API_BASE_URL + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data && data.detail ? data.detail : 'Une erreur est survenue';
    throw new ApiError(message, response.status);
  }

  return data;
}

export function registerUser(name, email, password) {
  return apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
}

export function loginUser(email, password) {
  return apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function getMeetings() {
  return apiRequest('/meetings', { method: 'GET' });
}

export function getMeetingSummary(meetingId) {
  return apiRequest(`/meetings/${meetingId}/summary`, { method: 'GET' });
}

export { ApiError };
