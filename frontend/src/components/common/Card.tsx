/**
 * Card Component
 *
 * Container component with optional header and footer.
 */

import React from 'react';
import clsx from 'clsx';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  shadow?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  padding = 'md',
  shadow = 'sm',
  hover = false,
}) => {
  const paddingStyles = {
    none: '',
    sm: 'p-3',
    md: 'p-4 lg:p-6',
    lg: 'p-6 lg:p-8',
  };

  const shadowStyles = {
    none: '',
    sm: 'shadow-sm',
    md: 'shadow-md',
    lg: 'shadow-lg',
  };

  return (
    <div
      className={clsx(
        'bg-white rounded-lg border border-gray-200',
        paddingStyles[padding],
        shadowStyles[shadow],
        hover && 'hover:shadow-md transition-shadow cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  );
};

export interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  children,
  className,
  action,
}) => (
  <div className={clsx('flex items-center justify-between mb-4', className)}>
    <div>{children}</div>
    {action && <div>{action}</div>}
  </div>
);

export interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
  subtitle?: string;
}

export const CardTitle: React.FC<CardTitleProps> = ({
  children,
  className,
  subtitle,
}) => (
  <div className={className}>
    <h3 className="text-lg font-semibold text-gray-900">{children}</h3>
    {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
  </div>
);

export interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({
  children,
  className,
}) => <div className={className}>{children}</div>;

export interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({
  children,
  className,
}) => (
  <div
    className={clsx(
      'mt-4 pt-4 border-t border-gray-100 flex items-center justify-end gap-3',
      className
    )}
  >
    {children}
  </div>
);

export default Card;
