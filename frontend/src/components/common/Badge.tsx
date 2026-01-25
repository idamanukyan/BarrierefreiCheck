/**
 * Badge Component
 *
 * Small status indicators and labels.
 */

import React from 'react';
import clsx from 'clsx';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  dot = false,
  className,
}) => {
  const variants = {
    default: 'bg-gray-100 text-gray-800',
    primary: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-purple-100 text-purple-800',
  };

  const dotColors = {
    default: 'bg-gray-500',
    primary: 'bg-blue-500',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    danger: 'bg-red-500',
    info: 'bg-purple-500',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-sm',
    lg: 'px-3 py-1 text-sm',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {dot && (
        <span
          className={clsx(
            'w-1.5 h-1.5 rounded-full mr-1.5',
            dotColors[variant]
          )}
        />
      )}
      {children}
    </span>
  );
};

// Impact badges for accessibility issues
export type ImpactLevel = 'critical' | 'serious' | 'moderate' | 'minor';

export interface ImpactBadgeProps {
  impact: ImpactLevel;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const ImpactBadge: React.FC<ImpactBadgeProps> = ({
  impact,
  size = 'md',
  showLabel = true,
}) => {
  const config: Record<ImpactLevel, { variant: BadgeProps['variant']; label: string }> = {
    critical: { variant: 'danger', label: 'Kritisch' },
    serious: { variant: 'warning', label: 'Schwerwiegend' },
    moderate: { variant: 'info', label: 'Mittel' },
    minor: { variant: 'default', label: 'Gering' },
  };

  const { variant, label } = config[impact];

  return (
    <Badge variant={variant} size={size} dot>
      {showLabel ? label : impact}
    </Badge>
  );
};

// WCAG level badges
export type WcagLevel = 'A' | 'AA' | 'AAA';

export interface WcagBadgeProps {
  level: WcagLevel;
  size?: 'sm' | 'md' | 'lg';
}

export const WcagBadge: React.FC<WcagBadgeProps> = ({ level, size = 'md' }) => {
  const variants: Record<WcagLevel, BadgeProps['variant']> = {
    A: 'success',
    AA: 'primary',
    AAA: 'info',
  };

  return (
    <Badge variant={variants[level]} size={size}>
      WCAG {level}
    </Badge>
  );
};

// Scan status badges
export type ScanStatus = 'queued' | 'crawling' | 'scanning' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface StatusBadgeProps {
  status: ScanStatus;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const config: Record<ScanStatus, { variant: BadgeProps['variant']; label: string }> = {
    queued: { variant: 'default', label: 'In Warteschlange' },
    crawling: { variant: 'info', label: 'Crawling' },
    scanning: { variant: 'primary', label: 'Scanning' },
    processing: { variant: 'info', label: 'Verarbeitung' },
    completed: { variant: 'success', label: 'Abgeschlossen' },
    failed: { variant: 'danger', label: 'Fehlgeschlagen' },
    cancelled: { variant: 'warning', label: 'Abgebrochen' },
  };

  const { variant, label } = config[status];

  return (
    <Badge variant={variant} size={size} dot>
      {label}
    </Badge>
  );
};

// Score badge
export interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

export const ScoreBadge: React.FC<ScoreBadgeProps> = ({ score, size = 'md' }) => {
  let variant: BadgeProps['variant'] = 'danger';
  if (score >= 90) variant = 'success';
  else if (score >= 70) variant = 'primary';
  else if (score >= 50) variant = 'warning';

  return (
    <Badge variant={variant} size={size}>
      {score}%
    </Badge>
  );
};

export default Badge;
