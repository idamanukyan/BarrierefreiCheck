/**
 * Translation Hook
 *
 * Custom hook that wraps react-i18next useTranslation with
 * additional formatting utilities.
 */

import { useTranslation as useI18nTranslation } from 'react-i18next';
import { useCallback } from 'react';
import {
  formatDate,
  formatNumber,
  formatPercent,
  formatCurrency,
  getCurrentLanguage,
  changeLanguage,
  type SupportedLanguage,
} from '../i18n';

export function useTranslation(namespace?: string) {
  const { t, i18n } = useI18nTranslation(namespace);

  const currentLanguage = getCurrentLanguage();

  const setLanguage = useCallback(async (lang: SupportedLanguage) => {
    await changeLanguage(lang);
  }, []);

  const formatRelativeTime = useCallback((date: Date | string): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 60) {
      return t('time.justNow');
    } else if (diffMinutes < 60) {
      const key = diffMinutes === 1 ? 'time.minutes' : 'time.minutes_plural';
      return t('time.ago', { time: t(key, { count: diffMinutes }) });
    } else if (diffHours < 24) {
      const key = diffHours === 1 ? 'time.hours' : 'time.hours_plural';
      return t('time.ago', { time: t(key, { count: diffHours }) });
    } else {
      const key = diffDays === 1 ? 'time.days' : 'time.days_plural';
      return t('time.ago', { time: t(key, { count: diffDays }) });
    }
  }, [t]);

  const formatDuration = useCallback((durationMs: number): string => {
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes}m`;
    } else if (minutes > 0) {
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${seconds}s`;
    }
  }, []);

  return {
    t,
    i18n,
    currentLanguage,
    setLanguage,
    formatDate,
    formatNumber,
    formatPercent,
    formatCurrency,
    formatRelativeTime,
    formatDuration,
  };
}

export default useTranslation;
