/**
 * Error Fallback Component
 *
 * Displayed when an unhandled error occurs in the React component tree.
 * Provides user-friendly error message and recovery options.
 */

import React from 'react';
import { FallbackProps } from 'react-error-boundary';
import { useTranslation } from 'react-i18next';

interface ErrorFallbackProps extends FallbackProps {
  title?: string;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
  title,
}) => {
  const { t } = useTranslation();

  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        {/* Error Icon */}
        <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-6">
          <svg
            className="h-8 w-8 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        {/* Error Title */}
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {title || t('error.title', 'Etwas ist schiefgelaufen')}
        </h1>

        {/* Error Message */}
        <p className="text-gray-600 mb-6">
          {t(
            'error.message',
            'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.'
          )}
        </p>

        {/* Error Details (development only) */}
        {process.env.NODE_ENV === 'development' && error && (
          <div className="mb-6 p-4 bg-gray-100 rounded-md text-left overflow-auto">
            <p className="text-sm font-mono text-red-600 break-words">
              {error.message}
            </p>
            {error.stack && (
              <pre className="text-xs text-gray-500 mt-2 whitespace-pre-wrap">
                {error.stack.split('\n').slice(0, 5).join('\n')}
              </pre>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={resetErrorBoundary}
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {t('error.tryAgain', 'Erneut versuchen')}
          </button>
          <button
            onClick={handleReload}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {t('error.reload', 'Seite neu laden')}
          </button>
          <button
            onClick={handleGoHome}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {t('error.goHome', 'Zur Startseite')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorFallback;
