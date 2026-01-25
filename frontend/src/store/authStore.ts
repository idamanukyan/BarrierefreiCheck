/**
 * Authentication Store
 *
 * Manages user authentication state using Zustand.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../services/api';

export interface User {
  id: string;
  email: string;
  name: string;
  company?: string;
  plan: 'free' | 'starter' | 'professional' | 'enterprise';
  createdAt: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
  updateUser: (data: Partial<User>) => void;
}

interface RegisterData {
  email: string;
  password: string;
  name: string;
  company?: string;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post('/auth/login', { email, password });
          const { user, token } = response.data;

          // Set token in API client
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Login fehlgeschlagen';
          set({ isLoading: false, error: message });
          throw new Error(message);
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post('/auth/register', data);
          const { user, token } = response.data;

          // Set token in API client
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Registrierung fehlgeschlagen';
          set({ isLoading: false, error: message });
          throw new Error(message);
        }
      },

      logout: () => {
        // Remove token from API client
        delete api.defaults.headers.common['Authorization'];

        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      checkAuth: async () => {
        const { token } = get();

        if (!token) {
          set({ isLoading: false, isAuthenticated: false });
          return;
        }

        try {
          // Set token in API client
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

          const response = await api.get('/auth/me');
          set({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch {
          // Token invalid, clear auth state
          delete api.defaults.headers.common['Authorization'];
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },

      clearError: () => set({ error: null }),

      updateUser: (data: Partial<User>) => {
        const { user } = get();
        if (user) {
          set({ user: { ...user, ...data } });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    }
  )
);

// Initialize auth check on app load
useAuthStore.getState().checkAuth();
