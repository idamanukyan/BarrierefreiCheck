/**
 * i18n Configuration
 *
 * Internationalization setup for the frontend using i18next.
 * German (de) is the default language, with English (en) as secondary.
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import de from './locales/de.json';
import en from './locales/en.json';

// Supported languages
export const SUPPORTED_LANGUAGES = ['de', 'en'] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

// Language display names
export const LANGUAGE_NAMES: Record<SupportedLanguage, string> = {
  de: 'Deutsch',
  en: 'English',
};

// Initialize i18next
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { translation: de },
      en: { translation: en },
    },
    fallbackLng: 'de',
    defaultNS: 'translation',
    interpolation: {
      escapeValue: false, // React already escapes by default
    },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    react: {
      useSuspense: true,
    },
  });

export default i18n;

/**
 * Get current language
 */
export function getCurrentLanguage(): SupportedLanguage {
  const lang = i18n.language?.substring(0, 2) as SupportedLanguage;
  return SUPPORTED_LANGUAGES.includes(lang) ? lang : 'de';
}

/**
 * Change language
 */
export async function changeLanguage(lang: SupportedLanguage): Promise<void> {
  await i18n.changeLanguage(lang);
}

/**
 * Format date according to current locale
 */
export function formatDate(date: Date | string | undefined | null, options?: Intl.DateTimeFormatOptions): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '-';
  const locale = getCurrentLanguage() === 'de' ? 'de-DE' : 'en-US';
  return d.toLocaleDateString(locale, options);
}

/**
 * Format number according to current locale
 */
export function formatNumber(num: number, options?: Intl.NumberFormatOptions): string {
  const locale = getCurrentLanguage() === 'de' ? 'de-DE' : 'en-US';
  return num.toLocaleString(locale, options);
}

/**
 * Format percentage
 */
export function formatPercent(value: number): string {
  return formatNumber(value, { style: 'percent', minimumFractionDigits: 0, maximumFractionDigits: 1 });
}

/**
 * Format currency (EUR)
 */
export function formatCurrency(amount: number): string {
  const locale = getCurrentLanguage() === 'de' ? 'de-DE' : 'en-US';
  return amount.toLocaleString(locale, { style: 'currency', currency: 'EUR' });
}
