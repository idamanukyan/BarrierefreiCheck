/**
 * API Service
 *
 * Axios-based API client for communicating with the backend.
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import type {
  User,
  Scan,
  Issue,
  Plan,
  Subscription,
  Usage,
  Payment,
  DashboardStats,
  PaginatedResponse,
} from '../types';

// API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Get auth token from localStorage
 * This ensures token is available even before Zustand store rehydrates
 */
const getStoredToken = (): string | null => {
  try {
    const authStorage = localStorage.getItem('auth-storage');
    if (authStorage) {
      const parsed = JSON.parse(authStorage);
      return parsed?.state?.token || null;
    }
  } catch {
    // Ignore parse errors
  }
  return null;
};

/**
 * Set auth token in axios defaults
 * Call this after login/register to ensure all subsequent requests are authenticated
 */
export const setAuthToken = (token: string | null): void => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

/**
 * Clear auth token from axios defaults
 * Call this on logout
 */
export const clearAuthToken = (): void => {
  delete api.defaults.headers.common['Authorization'];
};

// Request interceptor for auth token and logging
api.interceptors.request.use(
  (config) => {
    // Ensure auth token is set from storage if not already present
    // This handles race conditions during page refresh before Zustand rehydrates
    if (!config.headers['Authorization']) {
      const token = getStoredToken();
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
    }

    // Log requests in development
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle specific error codes
    if (error.response?.status === 401) {
      // Unauthorized - token expired or invalid
      // Clear auth state (handled by auth store)
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }

    return Promise.reject(error);
  }
);

// API response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  detail: string;
  code?: string;
}

// Generic request helper
async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await api.request<T>(config);
  return response.data;
}

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    request<{ user: User; token: string }>({
      method: 'POST',
      url: '/auth/login',
      data: { email, password },
    }),

  register: (data: { email: string; password: string; name: string; company?: string }) =>
    request<{ user: User; token: string }>({
      method: 'POST',
      url: '/auth/register',
      data,
    }),

  me: () => request<User>({ method: 'GET', url: '/auth/me' }),

  forgotPassword: (email: string) =>
    request<{ message: string }>({
      method: 'POST',
      url: '/auth/forgot-password',
      data: { email },
    }),

  resetPassword: (token: string, password: string) =>
    request<{ message: string }>({
      method: 'POST',
      url: '/auth/reset-password',
      data: { token, password },
    }),
};

// Scans API
export interface CreateScanData {
  url: string;
  crawl?: boolean;
  maxPages?: number;
  options?: {
    waitTime?: number;
    respectRobotsTxt?: boolean;
    captureScreenshots?: boolean;
  };
}

export const scansApi = {
  create: (data: CreateScanData) =>
    request<Scan>({
      method: 'POST',
      url: '/scans',
      data,
    }),

  list: (params?: { page?: number; pageSize?: number; status?: string }) =>
    request<PaginatedResponse<Scan>>({
      method: 'GET',
      url: '/scans',
      params,
    }),

  get: (scanId: string) =>
    request<Scan>({
      method: 'GET',
      url: `/scans/${scanId}`,
    }),

  getResults: (scanId: string) =>
    request<Scan>({
      method: 'GET',
      url: `/scans/${scanId}/results`,
    }),

  getIssues: (scanId: string, params?: { page?: number; impact?: string; wcagLevel?: string }) =>
    request<PaginatedResponse<Issue>>({
      method: 'GET',
      url: `/scans/${scanId}/issues`,
      params,
    }),

  delete: (scanId: string) =>
    request<void>({
      method: 'DELETE',
      url: `/scans/${scanId}`,
    }),

  cancel: (scanId: string) =>
    request<Scan>({
      method: 'POST',
      url: `/scans/${scanId}/cancel`,
    }),

  rescan: (scanId: string) =>
    request<Scan>({
      method: 'POST',
      url: `/scans/${scanId}/rescan`,
    }),
};

// Reports API
export interface CreateReportData {
  scanId: string;
  format: 'pdf' | 'html' | 'json' | 'csv';
  language?: 'de' | 'en';
  includeScreenshots?: boolean;
  branding?: {
    logo?: string;
    companyName?: string;
  };
}

export interface Report {
  id: string;
  scanId: string;
  format: 'pdf' | 'html' | 'json' | 'csv';
  language: 'de' | 'en';
  status: 'pending' | 'generating' | 'completed' | 'failed';
  downloadUrl?: string;
  createdAt: string;
  completedAt?: string;
}

export const reportsApi = {
  create: (data: CreateReportData) =>
    request<{ reportId: string; downloadUrl: string }>({
      method: 'POST',
      url: '/reports',
      data,
    }),

  list: (params?: { page?: number; pageSize?: number }) =>
    request<PaginatedResponse<Report>>({
      method: 'GET',
      url: '/reports',
      params,
    }),

  get: (reportId: string) =>
    request<Report>({
      method: 'GET',
      url: `/reports/${reportId}`,
    }),

  download: (reportId: string) => `${API_BASE_URL}/reports/${reportId}/download`,
};

// User API
export const userApi = {
  getProfile: () => request<User>({ method: 'GET', url: '/users/profile' }),

  updateProfile: (data: { name?: string; company?: string; phone?: string }) =>
    request<User>({
      method: 'PATCH',
      url: '/users/profile',
      data,
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ message: string }>({
      method: 'POST',
      url: '/users/change-password',
      data: { currentPassword, newPassword },
    }),

  getUsage: () =>
    request<{
      scansUsed: number;
      scansLimit: number;
      pagesScanned: number;
      periodStart: string;
      periodEnd: string;
    }>({
      method: 'GET',
      url: '/users/usage',
    }),
};

// Dashboard API
export const dashboardApi = {
  getStats: () =>
    request<DashboardStats>({
      method: 'GET',
      url: '/dashboard/stats',
    }),
};

// Export API - generates download URLs for existing backend endpoints
export const exportApi = {
  issuesUrl: (scanId: string, format: 'csv' | 'json', includeHtml = false) =>
    `${API_BASE_URL}/export/scans/${scanId}/issues?format=${format}&include_html=${includeHtml}`,

  summaryUrl: (scanId: string) =>
    `${API_BASE_URL}/export/scans/${scanId}/summary`,

  pagesUrl: (scanId: string, format: 'csv' | 'json') =>
    `${API_BASE_URL}/export/scans/${scanId}/pages?format=${format}`,
};

// Domains API
import type { Domain, DomainListResponse, BulkCreateResponse, BulkDeleteResponse } from '../types';

export interface CreateDomainData {
  domain: string;
  display_name?: string;
  description?: string;
}

export const domainsApi = {
  list: (includeInactive = false) =>
    request<DomainListResponse>({
      method: 'GET',
      url: '/domains',
      params: { include_inactive: includeInactive },
    }),

  create: (data: CreateDomainData) =>
    request<Domain>({
      method: 'POST',
      url: '/domains',
      data,
    }),

  bulkCreate: (domains: CreateDomainData[]) =>
    request<BulkCreateResponse>({
      method: 'POST',
      url: '/domains/bulk',
      data: { domains },
    }),

  get: (domainId: string) =>
    request<Domain>({
      method: 'GET',
      url: `/domains/${domainId}`,
    }),

  update: (domainId: string, data: { display_name?: string; description?: string; is_active?: boolean }) =>
    request<Domain>({
      method: 'PATCH',
      url: `/domains/${domainId}`,
      data,
    }),

  delete: (domainId: string) =>
    request<void>({
      method: 'DELETE',
      url: `/domains/${domainId}`,
    }),

  bulkDelete: (domainIds: string[]) =>
    request<BulkDeleteResponse>({
      method: 'DELETE',
      url: '/domains',
      params: { domain_ids: domainIds },
    }),
};

// Share Links API
export interface ShareLink {
  id: string;
  token_prefix: string;
  name: string | null;
  expires_at: string;
  is_active: boolean;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string;
}

export interface ShareLinkCreateResponse {
  link: ShareLink;
  token: string;
  share_url: string;
}

export interface ShareLinkListResponse {
  items: ShareLink[];
  total: number;
}

export interface SharedReportResponse {
  report: {
    id: string;
    format: string;
    language: string;
    status: string;
    created_at: string | null;
  };
  scan: {
    id: string;
    url: string;
    score: number | null;
    pages_scanned: number;
    issues_count: number;
    completed_at: string | null;
  };
  shared_by: string | null;
  expires_at: string;
}

export const shareLinksApi = {
  create: (reportId: string, data: { name?: string; expires_in_days?: number }) =>
    request<ShareLinkCreateResponse>({
      method: 'POST',
      url: `/reports/${reportId}/share`,
      data,
    }),

  list: (reportId: string) =>
    request<ShareLinkListResponse>({
      method: 'GET',
      url: `/reports/${reportId}/share`,
    }),

  revoke: (reportId: string, linkId: string) =>
    request<void>({
      method: 'DELETE',
      url: `/reports/${reportId}/share/${linkId}`,
    }),

  getShared: (token: string) =>
    request<SharedReportResponse>({
      method: 'GET',
      url: `/shared/${token}`,
    }),
};

export { setAuthToken, clearAuthToken };
export default api;
