// Module centralisant les appels vers l'API backend

// En local (127.0.0.1/localhost), on appelle le backend local. Sinon (site
// deploye), on appelle le backend deploye sur Railway.
const PRODUCTION_API_BASE_URL = 'https://scribe-production-a094.up.railway.app';

const API_BASE_URL = ['127.0.0.1', 'localhost'].includes(window.location.hostname)
  ? 'http://127.0.0.1:8000'
  : PRODUCTION_API_BASE_URL;

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

export function getMeetings(filters = {}) {
  const params = new URLSearchParams();
  if (filters.theme) params.set('theme', filters.theme);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);

  const query = params.toString();
  const path = query ? `/meetings?${query}` : '/meetings';

  return apiRequest(path, { method: 'GET' });
}

export function getMeetingSummary(meetingId) {
  return apiRequest(`/meetings/${meetingId}/summary`, { method: 'GET' });
}

export function getDiarizedTranscript(meetingId) {
  return apiRequest(`/meetings/${meetingId}/diarized-transcript`, { method: 'GET' });
}

export function getMeetingDetails(meetingId) {
  return apiRequest(`/meetings/${meetingId}/details`, { method: 'GET' });
}

export function startRecording(platform, nativeMeetingId, botName) {
  return apiRequest('/recording/start', {
    method: 'POST',
    body: JSON.stringify({ platform, native_meeting_id: nativeMeetingId, bot_name: botName }),
  });
}

export function stopRecording(recordingId) {
  return apiRequest(`/recording/${recordingId}/stop`, { method: 'POST' });
}

export function refreshTranscript(recordingId) {
  return apiRequest(`/recording/${recordingId}/transcript`, { method: 'GET' });
}

export function getActions(status = null) {
  const path = status ? `/actions?status=${encodeURIComponent(status)}` : '/actions';
  return apiRequest(path, { method: 'GET' });
}

export function getOpenActions() {
  return apiRequest('/actions/open', { method: 'GET' });
}

export function getMeetingsCount() {
  return getMeetings().then((meetings) => meetings.length);
}

export function updateActionStatus(actionId, status) {
  return apiRequest(`/actions/${actionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export { ApiError };
