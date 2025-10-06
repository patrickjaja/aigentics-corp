/**
 * i18next Configuration for Multi-Language Support
 *
 * Supports all 24 EU official languages with German and English as primary languages.
 * Includes proper formatting for dates, numbers, and currencies per locale.
 *
 * @see https://www.i18next.com/
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation resources
import de from './locales/de.json';
import en from './locales/en.json';
import fr from './locales/fr.json';
import es from './locales/es.json';
import it from './locales/it.json';
import nl from './locales/nl.json';
import pl from './locales/pl.json';
import pt from './locales/pt.json';
import cs from './locales/cs.json';
import da from './locales/da.json';
import el from './locales/el.json';
import hu from './locales/hu.json';
import ro from './locales/ro.json';
import sv from './locales/sv.json';
import bg from './locales/bg.json';
import hr from './locales/hr.json';
import et from './locales/et.json';
import fi from './locales/fi.json';
import ga from './locales/ga.json';
import lt from './locales/lt.json';
import lv from './locales/lv.json';
import mt from './locales/mt.json';
import sk from './locales/sk.json';
import sl from './locales/sl.json';

/**
 * All 24 EU official languages
 */
export const SUPPORTED_LANGUAGES = [
  'de', // German (primary)
  'en', // English (primary)
  'fr', // French
  'es', // Spanish
  'it', // Italian
  'nl', // Dutch
  'pl', // Polish
  'pt', // Portuguese
  'cs', // Czech
  'da', // Danish
  'el', // Greek
  'hu', // Hungarian
  'ro', // Romanian
  'sv', // Swedish
  'bg', // Bulgarian
  'hr', // Croatian
  'et', // Estonian
  'fi', // Finnish
  'ga', // Irish
  'lt', // Lithuanian
  'lv', // Latvian
  'mt', // Maltese
  'sk', // Slovak
  'sl', // Slovenian
] as const;

export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];

/**
 * Language display names in their native language
 */
export const LANGUAGE_NAMES: Record<SupportedLanguage, string> = {
  de: 'Deutsch',
  en: 'English',
  fr: 'Français',
  es: 'Español',
  it: 'Italiano',
  nl: 'Nederlands',
  pl: 'Polski',
  pt: 'Português',
  cs: 'Čeština',
  da: 'Dansk',
  el: 'Ελληνικά',
  hu: 'Magyar',
  ro: 'Română',
  sv: 'Svenska',
  bg: 'Български',
  hr: 'Hrvatski',
  et: 'Eesti',
  fi: 'Suomi',
  ga: 'Gaeilge',
  lt: 'Lietuvių',
  lv: 'Latviešu',
  mt: 'Malti',
  sk: 'Slovenčina',
  sl: 'Slovenščina',
};

/**
 * Translation resources organized by namespace
 */
const resources = {
  de: { translation: de },
  en: { translation: en },
  fr: { translation: fr },
  es: { translation: es },
  it: { translation: it },
  nl: { translation: nl },
  pl: { translation: pl },
  pt: { translation: pt },
  cs: { translation: cs },
  da: { translation: da },
  el: { translation: el },
  hu: { translation: hu },
  ro: { translation: ro },
  sv: { translation: sv },
  bg: { translation: bg },
  hr: { translation: hr },
  et: { translation: et },
  fi: { translation: fi },
  ga: { translation: ga },
  lt: { translation: lt },
  lv: { translation: lv },
  mt: { translation: mt },
  sk: { translation: sk },
  sl: { translation: sl },
};

/**
 * Currency formatting per locale
 * German uses: 1.234,56 €
 * English uses: €1,234.56
 */
export const formatCurrency = (amount: number, locale: string = 'de-DE'): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'EUR',
  }).format(amount);
};

/**
 * Date formatting per locale
 * German uses: DD.MM.YYYY
 * English uses: DD/MM/YYYY or MM/DD/YYYY
 */
export const formatDate = (date: Date, locale: string = 'de-DE'): string => {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
};

/**
 * Number formatting per locale
 * German uses: 1.234,56
 * English uses: 1,234.56
 */
export const formatNumber = (num: number, locale: string = 'de-DE', decimals: number = 2): string => {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
};

/**
 * Initialize i18next
 */
i18n
  .use(LanguageDetector) // Detect user language from browser/Accept-Language header
  .use(initReactI18next) // Pass i18n instance to react-i18next
  .init({
    resources,
    fallbackLng: 'de', // Default to German
    supportedLngs: SUPPORTED_LANGUAGES,

    // Namespace separation for better organization
    ns: ['translation'],
    defaultNS: 'translation',

    // Debug mode (disable in production)
    debug: process.env.NODE_ENV === 'development',

    // Language detection configuration
    detection: {
      order: ['querystring', 'cookie', 'localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage', 'cookie'],
      lookupQuerystring: 'lng',
      lookupCookie: 'i18next',
      lookupLocalStorage: 'i18nextLng',
    },

    // Interpolation configuration
    interpolation: {
      escapeValue: false, // React already escapes values

      // Custom formatters for dates, numbers, currency
      format: (value, format, lng) => {
        if (format === 'uppercase') return value.toUpperCase();
        if (format === 'lowercase') return value.toLowerCase();

        // Date formatting
        if (value instanceof Date) {
          return formatDate(value, lng || 'de-DE');
        }

        // Currency formatting
        if (format === 'currency') {
          return formatCurrency(Number(value), lng || 'de-DE');
        }

        // Number formatting
        if (format === 'number') {
          return formatNumber(Number(value), lng || 'de-DE');
        }

        return value;
      },
    },

    // Pluralization rules (i18next handles this automatically for most languages)
    pluralSeparator: '_',

    // React configuration
    react: {
      useSuspense: true,
      bindI18n: 'languageChanged loaded',
      bindI18nStore: 'added removed',
      transEmptyNodeValue: '',
      transSupportBasicHtmlNodes: true,
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'p'],
    },

    // Loading configuration
    load: 'languageOnly', // Load only 'de', not 'de-DE'

    // Missing key handler (for development)
    saveMissing: process.env.NODE_ENV === 'development',
    missingKeyHandler: (lng, ns, key) => {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`Missing translation key: ${key} for language: ${lng}`);
      }
    },
  });

export default i18n;

/**
 * Helper hook for language-specific formatting
 */
export const useFormatters = () => {
  const { i18n } = { i18n };
  const locale = i18n.language;

  return {
    formatCurrency: (amount: number) => formatCurrency(amount, locale),
    formatDate: (date: Date) => formatDate(date, locale),
    formatNumber: (num: number, decimals?: number) => formatNumber(num, locale, decimals),
  };
};

/**
 * German business standards helpers
 */
export const germanFormatting = {
  /**
   * Format currency in German style: 1.234,56 €
   */
  currency: (amount: number): string => formatCurrency(amount, 'de-DE'),

  /**
   * Format date in German style: DD.MM.YYYY
   */
  date: (date: Date): string => formatDate(date, 'de-DE'),

  /**
   * Format number in German style: 1.234,56
   */
  number: (num: number, decimals: number = 2): string => formatNumber(num, 'de-DE', decimals),

  /**
   * Format time in German style: HH:MM
   */
  time: (date: Date): string => {
    return new Intl.DateTimeFormat('de-DE', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  },

  /**
   * Format datetime in German style: DD.MM.YYYY HH:MM
   */
  datetime: (date: Date): string => {
    return new Intl.DateTimeFormat('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  },
};
