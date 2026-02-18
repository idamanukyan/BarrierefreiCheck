/**
 * Error Fallback Component
 *
 * Displayed when an unhandled error occurs in the React component tree.
 * Provides user-friendly error message and recovery options.
 * Includes error reporting functionality and improved accessibility.
 */

import React, { useState, useEffect } from 'react';
import { FallbackProps } from 'react-error-boundary';
import { useTranslation } from 'react-i18next';

interface ErrorFallbackProps extends FallbackProps {
  title?: string;
}

// Generate a unique error ID for tracking
const generateErrorId = () => {
  return `err_${Date.now().toString(36)}_${Math.random().toString(36).substr(2, 9)}`;
};

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
  title,
}) => {
  const { t } = useTranslation();
  const [errorId] = useState(generateErrorId);
  const [isReporting, setIsReporting] = useState(false);
  const [reportSent, setReportSent] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // Log error to console with ID for debugging
  useEffect(() => {
    console.error(`[Error ${errorId}]`, error);
  }, [errorId, error]);

  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleReload = () => {
    window.location.reload();
  };

  const handleReportError = async () => {
    setIsReporting(true);
    try {
      // In production, this would send to your error reporting service
      const errorReport = {
        errorId,
        message: error?.message,
        stack: error?.stack,
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString(),
      };

      // Log for now, in production send to API
      console.log('Error report:', errorReport);

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));

      setReportSent(true);
    } catch {
      console.error('Failed to send error report');
    } finally {
      setIsReporting(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-gray-50 px-4"
      role="alert"
      aria-live="assertive"
    >
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        {/* Error Icon */}
        <div
          className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-6"
          aria-hidden="true"
        >
          <svg
            className="h-8 w-8 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
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
        <p className="text-gray-600 mb-4">
          {t(
            'error.message',
            'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.'
          )}
        </p>

        {/* Error ID for support */}
        <p className="text-xs text-gray-400 mb-6">
          {t('error.errorId', 'Fehler-ID')}: <code className="bg-gray-100 px-1 rounded">{errorId}</code>
        </p>

        {/* Toggle Details Button */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:text-blue-800 mb-4 focus:outline-none focus:underline"
          aria-expanded={showDetails}
        >
          {showDetails
            ? t('error.hideDetails', 'Details ausblenden')
            : t('error.showDetails', 'Details anzeigen')}
        </button>

        {/* Error Details (toggleable) */}
        {showDetails && error && (
          <div
            className="mb-6 p-4 bg-gray-100 rounded-md text-left overflow-auto max-h-48"
            role="region"
            aria-label={t('error.technicalDetails', 'Technische Details')}
          >
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
        <div className="flex flex-col gap-3">
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

          {/* Report Error Button */}
          <button
            onClick={handleReportError}
            disabled={isReporting || reportSent}
            className={`inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
              reportSent
                ? 'bg-green-100 text-green-800 cursor-default'
                : 'text-blue-600 hover:text-blue-800 hover:bg-blue-50'
            }`}
            aria-live="polite"
          >
            {isReporting ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {t('error.reporting', 'Wird gemeldet...')}
              </>
            ) : reportSent ? (
              <>
                <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {t('error.reported', 'Fehler gemeldet')}
              </>
            ) : (
              t('error.reportError', 'Fehler melden')
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorFallback;
