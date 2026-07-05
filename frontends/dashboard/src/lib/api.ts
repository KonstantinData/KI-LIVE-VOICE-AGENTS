/** Fetch Wrapper für die Backend-API. */

import { getToken, removeToken } from './auth';

const DEFAULT_API_URL = import.meta.env.PROD
  ? 'https://api.mein-kuechenexperte.de'
  : 'http://localhost:8000';
const API_URL = import.meta.env.VITE_API_URL ?? DEFAULT_API_URL;

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...options.headers,
  };

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    removeToken();
    window.location.href = '/login';
    throw new Error('Nicht authentifiziert');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function download(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, { headers: authHeaders() });

  if (response.status === 401) {
    removeToken();
    window.location.href = '/login';
    throw new Error('Nicht authentifiziert');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Download fehlgeschlagen' }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  download,
};
