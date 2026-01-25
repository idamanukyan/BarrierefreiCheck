/**
 * API Service
 *
 * Axios-based API client for communicating with the backend.
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';

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

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
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
    request<{ user: any; token: string }>({
      method: 'POST',
      url: '/auth/login',
      data: { email, password },
    }),

  register: (data: { email: string; password: string; name: string; company?: string }) =>
    request<{ user: any; token: string }>({
      method: 'POST',
      url: '/auth/register',
      data,
    }),

  me: () => request<any>({ method: 'GET', url: '/auth/me' }),

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
    request<any>({
      method: 'POST',
      url: '/scans',
      data,
    }),

  list: (params?: { page?: number; pageSize?: number; status?: string }) =>
    request<PaginatedResponse<any>>({
      method: 'GET',
      url: '/scans',
      params,
    }),

  get: (scanId: string) =>
    request<any>({
      method: 'GET',
      url: `/scans/${scanId}`,
    }),

  getResults: (scanId: string) =>
    request<any>({
      method: 'GET',
      url: `/scans/${scanId}/results`,
    }),

  getIssues: (scanId: string, params?: { page?: number; impact?: string; wcagLevel?: string }) =>
    request<PaginatedResponse<any>>({
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
    request<any>({
      method: 'POST',
      url: `/scans/${scanId}/cancel`,
    }),

  rescan: (scanId: string) =>
    request<any>({
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

export const reportsApi = {
  create: (data: CreateReportData) =>
    request<{ reportId: string; downloadUrl: string }>({
      method: 'POST',
      url: '/reports',
      data,
    }),

  list: (params?: { page?: number; pageSize?: number }) =>
    request<PaginatedResponse<any>>({
      method: 'GET',
      url: '/reports',
      params,
    }),

  get: (reportId: string) =>
    request<any>({
      method: 'GET',
      url: `/reports/${reportId}`,
    }),

  download: (reportId: string) => `${API_BASE_URL}/reports/${reportId}/download`,
};

// User API
export const userApi = {
  getProfile: () => request<any>({ method: 'GET', url: '/users/profile' }),

  updateProfile: (data: { name?: string; company?: string; phone?: string }) =>
    request<any>({
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
    request<{
      totalScans: number;
      pagesScanned: number;
      issuesFound: number;
      averageScore: number;
      recentScans: any[];
      issuesByImpact: Record<string, number>;
      issuesByWcag: Record<string, number>;
      scoreHistory: { date: string; score: number }[];
    }>({
      method: 'GET',
      url: '/dashboard/stats',
    }),
};

export default api;
