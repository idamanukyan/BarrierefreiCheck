/**
 * Auth Layout
 *
 * Layout for authentication pages (login, register, forgot password).
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from '../../hooks/useTranslation';
import { LanguageSwitcher } from '../common/LanguageSwitcher';

interface AuthLayoutProps {
  children: React.ReactNode;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4">
        <NavLink to="/" className="flex items-center space-x-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-lg">
            BC
          </div>
          <span className="text-xl font-bold text-gray-900">
            {t('common.appName')}
          </span>
        </NavLink>
        <LanguageSwitcher variant="minimal" />
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-sm text-gray-500">
        <p>{t('footer.copyright', { year: new Date().getFullYear() })}</p>
        <div className="mt-2 flex items-center justify-center space-x-4">
          <a href="/impressum" className="hover:text-gray-700">
            {t('footer.imprint')}
          </a>
          <span>|</span>
          <a href="/datenschutz" className="hover:text-gray-700">
            {t('footer.privacy')}
          </a>
          <span>|</span>
          <a href="/agb" className="hover:text-gray-700">
            {t('footer.terms')}
          </a>
        </div>
      </footer>

      {/* Background decoration */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-blue-100 opacity-50 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-purple-100 opacity-50 blur-3xl" />
      </div>
    </div>
  );
};

export default AuthLayout;
