/**
 * Alert Component
 *
 * Notification messages for success, error, warning, and info states.
 */

import React from 'react';
import clsx from 'clsx';

export interface AlertProps {
  children: React.ReactNode;
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
  icon?: React.ReactNode;
}

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = 'info',
  title,
  dismissible = false,
  onDismiss,
  className,
  icon,
}) => {
  const variants = {
    info: {
      container: 'bg-blue-50 border-blue-200 text-blue-800',
      icon: 'text-blue-500',
      title: 'text-blue-800',
    },
    success: {
      container: 'bg-green-50 border-green-200 text-green-800',
      icon: 'text-green-500',
      title: 'text-green-800',
    },
    warning: {
      container: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      icon: 'text-yellow-500',
      title: 'text-yellow-800',
    },
    error: {
      container: 'bg-red-50 border-red-200 text-red-800',
      icon: 'text-red-500',
      title: 'text-red-800',
    },
  };

  const icons = {
    info: InfoIcon,
    success: CheckIcon,
    warning: WarningIcon,
    error: ErrorIcon,
  };

  const IconComponent = icons[variant];
  const styles = variants[variant];

  return (
    <div
      className={clsx(
        'rounded-lg border p-4',
        styles.container,
        className
      )}
      role="alert"
    >
      <div className="flex">
        <div className={clsx('flex-shrink-0', styles.icon)}>
          {icon || <IconComponent className="h-5 w-5" />}
        </div>
        <div className="ml-3 flex-1">
          {title && (
            <h3 className={clsx('text-sm font-medium', styles.title)}>
              {title}
            </h3>
          )}
          <div className={clsx('text-sm', title && 'mt-1')}>
            {children}
          </div>
        </div>
        {dismissible && onDismiss && (
          <button
            onClick={onDismiss}
            className={clsx(
              'ml-auto -mx-1.5 -my-1.5 rounded-lg p-1.5 inline-flex h-8 w-8',
              'hover:bg-black hover:bg-opacity-10 focus:ring-2 focus:ring-offset-2',
              variant === 'info' && 'focus:ring-blue-500',
              variant === 'success' && 'focus:ring-green-500',
              variant === 'warning' && 'focus:ring-yellow-500',
              variant === 'error' && 'focus:ring-red-500'
            )}
            aria-label="Dismiss"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  );
};

// Icons
const InfoIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path
      fillRule="evenodd"
      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
      clipRule="evenodd"
    />
  </svg>
);

const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path
      fillRule="evenodd"
      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
      clipRule="evenodd"
    />
  </svg>
);

const WarningIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path
      fillRule="evenodd"
      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
      clipRule="evenodd"
    />
  </svg>
);

const ErrorIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path
      fillRule="evenodd"
      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
      clipRule="evenodd"
    />
  </svg>
);

const CloseIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 20 20">
    <path
      fillRule="evenodd"
      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
      clipRule="evenodd"
    />
  </svg>
);

export default Alert;
