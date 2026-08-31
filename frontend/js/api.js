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

export function getSpeakingTime(meetingId) {
  return apiRequest(`/meetings/${meetingId}/speaking-time`, { method: 'GET' });
}

export function getMeetingDetails(meetingId) {
  return apiRequest(`/meetings/${meetingId}/details`, { method: 'GET' });
}

export function getDiarizeStatus(meetingId) {
  return apiRequest(`/meetings/${meetingId}/diarize-status`, { method: 'GET' });
}

export function anonymizeMeeting(meetingId) {
  return apiRequest(`/meetings/${meetingId}/anonymize`, { method: 'POST' });
}

export function generateSummary(meetingId) {
  return apiRequest(`/meetings/${meetingId}/generate-summary`, { method: 'POST' });
}

export function extractActions(meetingId) {
  return apiRequest(`/meetings/${meetingId}/extract-actions`, { method: 'POST' });
}

export function updateMeetingTheme(meetingId, theme) {
  return apiRequest(`/meetings/${meetingId}/theme`, {
    method: 'PATCH',
    body: JSON.stringify({ theme }),
  });
}

export function startRecording(platform, nativeMeetingId, botName, meetingUrl) {
  return apiRequest('/recording/start', {
    method: 'POST',
    body: JSON.stringify({ platform, native_meeting_id: nativeMeetingId, bot_name: botName, meeting_url: meetingUrl }),
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

export function getOverdueActions() {
  return apiRequest('/actions/overdue', { method: 'GET' });
}

export function getDashboardTrends(granularity = 'day', periods = 8) {
  return apiRequest(`/dashboard/trends?granularity=${granularity}&periods=${periods}`, { method: 'GET' });
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

export function updateActionDueDate(actionId, dueDate) {
  return apiRequest(`/actions/${actionId}/due-date`, {
    method: 'PATCH',
    body: JSON.stringify({ due_date: dueDate || null }),
  });
}

export function deleteAction(actionId) {
  return apiRequest(`/actions/${actionId}`, { method: 'DELETE' });
}

export function deleteMeeting(meetingId) {
  return apiRequest(`/meetings/${meetingId}`, { method: 'DELETE' });
}


export function createDictaphoneRecording() {
  return apiRequest('/meetings', { method: 'POST' });
}

export async function uploadAudioFile(recordingId, file) {
  const token = sessionStorage.getItem('access_token');
  const formData = new FormData();
  formData.append('audio', file, file.name);
  const response = await fetch(`${API_BASE_URL}/meetings/${recordingId}/upload-audio`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(data?.detail ?? 'Une erreur est survenue', response.status);
  }
  return data;
}

export async function exportMeetingPdf(meetingId) {
  const token = sessionStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/export-pdf`, {
    method: 'GET',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(data?.detail ?? 'Une erreur est survenue', response.status);
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : `compte-rendu-${meetingId}.pdf`;

  return { blob, filename };
}

export function transcribeRecording(recordingId) {
  return apiRequest(`/meetings/${recordingId}/transcribe`, { method: 'POST' });
}

export function deleteAccount() {
  return apiRequest('/users/me', { method: 'DELETE' });
}

export async function exportPdf(meetingId) {
  const token = sessionStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/export-pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(data?.detail ?? 'Export échoué', response.status);
  }
  return response.blob();
}

export async function exportDocx(meetingId) {
  const token = sessionStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/export-docx`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(data?.detail ?? 'Export échoué', response.status);
  }
  return response.blob();
}

export { ApiError };
