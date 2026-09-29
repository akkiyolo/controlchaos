/**
 * ControlChaos API Client
 * Handles JWT storage, authorization headers, token refreshing, and error envelopes.
 */

const API_BASE = '/api/v1';

export class ApiClient {
  static getToken() {
    return localStorage.getItem('cc_access_token');
  }

  static getRefreshToken() {
    return localStorage.getItem('cc_refresh_token');
  }

  static setTokens(accessToken, refreshToken) {
    if (accessToken) localStorage.setItem('cc_access_token', accessToken);
    if (refreshToken) localStorage.setItem('cc_refresh_token', refreshToken);
  }

  static clearTokens() {
    localStorage.removeItem('cc_access_token');
    localStorage.removeItem('cc_refresh_token');
    localStorage.removeItem('cc_user');
  }

  static getCurrentUser() {
    const raw = localStorage.getItem('cc_user');
    return raw ? JSON.parse(raw) : null;
  }

  static setCurrentUser(user) {
    localStorage.setItem('cc_user', JSON.stringify(user));
  }

  static async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      let response = await fetch(url, { ...options, headers });

      // Handle 401 Unauthorized by trying to refresh once
      if (response.status === 401 && this.getRefreshToken() && !options._isRetry) {
        const refreshed = await this.refresh();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getToken()}`;
          response = await fetch(url, { ...options, headers, _isRetry: true });
        } else {
          this.clearTokens();
          window.location.hash = '#login';
          throw new Error('Session expired. Please log in again.');
        }
      }

      if (!response.ok) {
        let errorDetail = 'API request failed';
        try {
          const errData = await response.json();
          errorDetail = errData.detail || errData.error || errorDetail;
        } catch (_) {}
        throw new Error(errorDetail);
      }

      return await response.json();
    } catch (err) {
      throw err;
    }
  }

  static async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setTokens(data.access_token, data.refresh_token);
    const user = await this.getMe();
    this.setCurrentUser(user);
    return user;
  }

  static async refresh() {
    const rToken = this.getRefreshToken();
    if (!rToken) return false;
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rToken }),
      });
      if (res.ok) {
        const data = await res.json();
        this.setTokens(data.access_token, data.refresh_token);
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  static async getMe() {
    return await this.request('/auth/me');
  }

  static logout() {
    this.clearTokens();
    window.location.hash = '#login';
  }

  static async getHealth() {
    return await this.request('/health');
  }

  static async getReadiness() {
    return await this.request('/ready');
  }

  static async getProvidersStatus() {
    return await this.request('/providers/status');
  }

  static async listAuditLogs(page = 1, pageSize = 50, action = null) {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (action) params.append('action', action);
    return await this.request(`/audit/list?${params.toString()}`);
  }

  static async verifyAuditChain() {
    return await this.request('/audit/verify');
  }
}
