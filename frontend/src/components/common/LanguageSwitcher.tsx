/**
 * Language Switcher Component
 *
 * Allows users to switch between German and English.
 */

import React from 'react';
import { useTranslation } from '../../hooks/useTranslation';
import { SUPPORTED_LANGUAGES, LANGUAGE_NAMES, type SupportedLanguage } from '../../i18n';

interface LanguageSwitcherProps {
  variant?: 'dropdown' | 'buttons' | 'minimal';
  className?: string;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  variant = 'dropdown',
  className = '',
}) => {
  const { currentLanguage, setLanguage, t } = useTranslation();

  const handleLanguageChange = async (lang: SupportedLanguage) => {
    await setLanguage(lang);
  };

  if (variant === 'buttons') {
    return (
      <div className={`flex gap-2 ${className}`}>
        {SUPPORTED_LANGUAGES.map((lang) => (
          <button
            key={lang}
            onClick={() => handleLanguageChange(lang)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              currentLanguage === lang
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
            aria-pressed={currentLanguage === lang}
            aria-label={`${t('settings.language.select')}: ${LANGUAGE_NAMES[lang]}`}
          >
            {LANGUAGE_NAMES[lang]}
          </button>
        ))}
      </div>
    );
  }

  if (variant === 'minimal') {
    return (
      <div className={`flex gap-1 text-sm ${className}`}>
        {SUPPORTED_LANGUAGES.map((lang, index) => (
          <React.Fragment key={lang}>
            {index > 0 && <span className="text-gray-400">|</span>}
            <button
              onClick={() => handleLanguageChange(lang)}
              className={`transition-colors ${
                currentLanguage === lang
                  ? 'text-blue-600 font-medium'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              aria-pressed={currentLanguage === lang}
            >
              {lang.toUpperCase()}
            </button>
          </React.Fragment>
        ))}
      </div>
    );
  }

  // Default: dropdown
  return (
    <div className={`relative ${className}`}>
      <select
        value={currentLanguage}
        onChange={(e) => handleLanguageChange(e.target.value as SupportedLanguage)}
        className="appearance-none bg-white border border-gray-300 rounded-md px-4 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer"
        aria-label={t('settings.language.select')}
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang} value={lang}>
            {LANGUAGE_NAMES[lang]}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
        <svg
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </div>
    </div>
  );
};

export default LanguageSwitcher;
