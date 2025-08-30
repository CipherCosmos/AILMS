import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios instance with auth
const api = axios.create({ baseURL: API });

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

api.interceptors.request.use((config) => {
  const t = localStorage.getItem("access_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        // Redirect to login
        localStorage.clear();
        window.location.href = "/";
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${API}/auth/refresh`, { refresh_token: refreshToken }, {
          headers: { 'Content-Type': 'application/json' }
        });
        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem("access_token", access_token);
        if (newRefreshToken) localStorage.setItem("refresh_token", newRefreshToken);
        api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.clear();
        window.location.href = "/";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Enhanced API service with caching and additional features
class ApiService {
  constructor() {
    this.loadingStates = new Map();
    this.errorStates = new Map();
    this.cache = new Map();
    this.CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
  }

  // Get cached data if available and not expired
  getCached(key) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.CACHE_DURATION) {
      return cached.data;
    }
    return null;
  }

  // Set cache data
  setCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  // Clear cache for specific key or pattern
  clearCache(keyPattern) {
    if (keyPattern) {
      for (const key of this.cache.keys()) {
        if (key.includes(keyPattern)) {
          this.cache.delete(key);
        }
      }
    } else {
      this.cache.clear();
    }
  }

  // Set loading state
  setLoading(key, loading) {
    this.loadingStates.set(key, loading);
  }

  // Get loading state
  getLoading(key) {
    return this.loadingStates.get(key) || false;
  }

  // Set error state
  setError(key, error) {
    this.errorStates.set(key, error);
  }

  // Get error state
  getError(key) {
    return this.errorStates.get(key);
  }

  // Clear error state
  clearError(key) {
    this.errorStates.delete(key);
  }

  // Enhanced GET with caching
  async get(url, config = {}, options = {}) {
    const {
      useCache = true,
      cacheKey = url,
      showLoading = true,
      loadingKey = url
    } = options;

    // Check cache first
    if (useCache) {
      const cachedData = this.getCached(cacheKey);
      if (cachedData) {
        return { data: cachedData, cached: true };
      }
    }

    // Set loading state
    if (showLoading) {
      this.setLoading(loadingKey, true);
    }

    try {
      this.clearError(loadingKey);
      const response = await api.get(url, config);

      // Cache the response
      if (useCache) {
        this.setCache(cacheKey, response.data);
      }

      return { data: response.data, cached: false };
    } catch (error) {
      const errorMessage = this.handleError(error);
      this.setError(loadingKey, errorMessage);
      throw error;
    } finally {
      if (showLoading) {
        this.setLoading(loadingKey, false);
      }
    }
  }

  // Enhanced POST
  async post(url, data, config = {}, options = {}) {
    const { showLoading = true, loadingKey = url } = options;

    if (showLoading) {
      this.setLoading(loadingKey, true);
    }

    try {
      this.clearError(loadingKey);
      const response = await api.post(url, data, config);

      // Clear related cache
      this.clearCache(url.split('/')[1]);

      return response.data;
    } catch (error) {
      const errorMessage = this.handleError(error);
      this.setError(loadingKey, errorMessage);
      throw error;
    } finally {
      if (showLoading) {
        this.setLoading(loadingKey, false);
      }
    }
  }

  // Handle different types of errors
  handleError(error) {
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 400:
          return data.detail || 'Bad request. Please check your input.';
        case 401:
          return 'Authentication required. Please log in again.';
        case 403:
          return 'You do not have permission to perform this action.';
        case 404:
          return 'The requested resource was not found.';
        case 422:
          return 'Validation error. Please check your input.';
        case 500:
          return 'Server error. Please try again later.';
        default:
          return data.detail || `Error ${status}: ${data.message || 'Unknown error'}`;
      }
    } else if (error.request) {
      return 'Network error. Please check your connection and try again.';
    } else {
      return error.message || 'An unexpected error occurred.';
    }
  }
}

// Create singleton instance
const apiService = new ApiService();

export { apiService };
export default api;