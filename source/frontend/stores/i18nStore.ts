import { defineStore } from 'pinia';
import { LOCALES, MESSAGES, type Locale, type TranslationKey } from '../lib/translations';

const STORAGE_KEY = 'koshi_locale';
const FALLBACK: Locale = 'en';

export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && (LOCALES as readonly string[]).includes(value);
}

/**
 * Pick a starting locale: an explicit past choice wins, then the browser's
 * preference, then English.
 *
 * `navigator.language` is matched on its primary subtag only, so "vi-VN" counts
 * as Vietnamese.
 */
export function detectLocale(
  stored: string | null,
  navigatorLanguages: readonly string[] = [],
): Locale {
  if (isLocale(stored)) return stored;
  for (const tag of navigatorLanguages) {
    const primary = String(tag).toLowerCase().split('-')[0];
    if (isLocale(primary)) return primary;
  }
  return FALLBACK;
}

export const useI18nStore = defineStore('i18nStore', {
  state: () => ({
    locale: FALLBACK as Locale,
  }),

  getters: {
    /**
     * Translate a key. Missing keys return the key itself rather than an empty
     * string, so a gap is visible in the UI instead of silently blank.
     */
    t(state) {
      return (key: TranslationKey): string => MESSAGES[state.locale][key] ?? key;
    },
  },

  actions: {
    init() {
      if (typeof window === 'undefined') return;
      this.setLocale(
        detectLocale(window.localStorage.getItem(STORAGE_KEY), navigator.languages ?? [navigator.language]),
      );
    },

    setLocale(locale: Locale) {
      this.locale = locale;
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(STORAGE_KEY, locale);
        document.documentElement.setAttribute('lang', locale);
      }
    },

    toggleLocale() {
      const index = LOCALES.indexOf(this.locale);
      this.setLocale(LOCALES[(index + 1) % LOCALES.length]!);
    },
  },
});
