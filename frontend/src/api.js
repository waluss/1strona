const API_BASE = '/api/v1';

class ApiClient {
    constructor() {
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    setTokens(access, refresh) {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    }

    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }

    async request(endpoint, options = {}) {
        const headers = options.headers || {};
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        headers['Content-Type'] = 'application/json';

        const config = { ...options, headers };

        let response;
        try {
            response = await fetch(`${API_BASE}${endpoint}`, config);
            if (response.status === 404 && window.location.port === "8085") {
                // Fallback to direct backend port if reverse proxy is not loaded or during static dev
                response = await fetch(`http://localhost:8005/api/v1${endpoint}`, config);
            }
        } catch (e) {
            if (window.location.port === "8085") {
                response = await fetch(`http://localhost:8005/api/v1${endpoint}`, config);
            } else {
                throw e;
            }
        }

        if (response.status === 401) {
            this.clearTokens();
            window.location.hash = '#login';
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'API Request Failed' }));
            throw new Error(err.detail || 'API Request Failed');
        }

        return response.json();
    }

    login(username, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    }

    getMe() {
        return this.request('/auth/me');
    }

    changePassword(old_password, new_password) {
        return this.request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ old_password, new_password })
        });
    }

    getTenders(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/tenders?${query}`);
    }

    getTenderDetails(id) {
        return this.request(`/tenders/${id}`);
    }

    getTenderNotices(id) {
        return this.request(`/tenders/${id}/notices`);
    }

    getTenderScores(id) {
        return this.request(`/tenders/${id}/scores`);
    }

    getProfiles() {
        return this.request('/profiles');
    }

    createProfile(data) {
        return this.request('/profiles', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    activateProfile(id) {
        return this.request(`/profiles/${id}/activate`, {
            method: 'POST'
        });
    }

    runDryRun(params) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/imports/tenders/dry-run?${query}`, {
            method: 'POST'
        });
    }

    runImport(params) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/imports/tenders?${query}`, {
            method: 'POST'
        });
    }

    getImportRuns() {
        return this.request('/imports/runs');
    }

    getTenants() {
        return this.request('/tenants');
    }

    createTenant(name) {
        return this.request('/tenants', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
    }
}

export const api = new ApiClient();
