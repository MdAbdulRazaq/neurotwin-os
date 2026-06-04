import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getToken(key: string): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(key) || '';
}

function setToken(key: string, value: string): void {
  if (typeof window !== 'undefined') localStorage.setItem(key, value);
}

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach access token to every request
apiClient.interceptors.request.use(config => {
  const token = getToken('nt_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
apiClient.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise(resolve => {
          subscribeTokenRefresh(token => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          });
        });
      }

      isRefreshing = true;
      try {
        const refreshToken = getToken('nt_refresh_token');
        const resp = await axios.post(`${BASE_URL}/v1/auth/refresh`, { refresh_token: refreshToken });
        const { access_token, refresh_token } = resp.data;
        setToken('nt_access_token', access_token);
        setToken('nt_refresh_token', refresh_token);
        onRefreshed(access_token);
        original.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(original);
      } catch (refreshErr) {
        // Clear tokens and redirect to login
        if (typeof window !== 'undefined') {
          localStorage.removeItem('nt_access_token');
          localStorage.removeItem('nt_refresh_token');
          window.location.href = '/auth/login';
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// Auth helpers
export const authApi = {
  login: async (email: string, password: string) => {
    const resp = await apiClient.post('/v1/auth/login', { email, password });
    setToken('nt_access_token', resp.data.access_token);
    setToken('nt_refresh_token', resp.data.refresh_token);
    return resp.data;
  },
  register: async (name: string, email: string, password: string) => {
    const resp = await apiClient.post('/v1/auth/register', { name, email, password });
    setToken('nt_access_token', resp.data.access_token);
    setToken('nt_refresh_token', resp.data.refresh_token);
    return resp.data;
  },
  logout: async () => {
    await apiClient.post('/v1/auth/logout');
    localStorage.removeItem('nt_access_token');
    localStorage.removeItem('nt_refresh_token');
  },
};

// User API
export const userApi = {
  getProfile: () => apiClient.get('/v1/user/me').then(r => r.data),
  updatePreferences: (prefs: object) => apiClient.patch('/v1/user/preferences', prefs).then(r => r.data),
};

// Memory API
export const memoryApi = {
  list: (page = 0, limit = 20) =>
    apiClient.get(`/v1/memory?offset=${page * limit}&limit=${limit}`).then(r => r.data),
  delete: (ids: string[]) =>
    apiClient.delete('/v1/memory', { data: { memory_ids: ids } }).then(r => r.data),
};

// Analytics API
export const analyticsApi = {
  summary: (days = 7) =>
    apiClient.get(`/v1/analytics/summary?days=${days}`).then(r => r.data),
  moodTimeline: (days = 30) =>
    apiClient.get(`/v1/analytics/mood?days=${days}`).then(r => r.data),
};
