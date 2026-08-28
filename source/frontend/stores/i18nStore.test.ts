/**
 * Tests for locale selection and translation completeness (D5 GAP-11).
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useI18nStore, detectLocale, isLocale } from './i18nStore';
import { MESSAGES, LOCALES, LOCALE_LABELS } from '../lib/translations';

beforeEach(() => setActivePinia(createPinia()));

describe('translation dictionary', () => {
  it('defines every locale in LOCALES', () => {
    for (const loc of LOCALES) {
      expect(MESSAGES[loc]).toBeDefined();
      expect(LOCALE_LABELS[loc]).toBeTruthy();
    }
  });

  it('has no missing or empty strings in any locale', () => {
    // The English dictionary is the source of truth; a key present there and
    // absent (or blank) elsewhere would render as a raw key in the UI.
    const keys = Object.keys(MESSAGES.en);
    expect(keys.length).toBeGreaterThan(50);

    for (const loc of LOCALES) {
      const missing = keys.filter((k) => !(MESSAGES[loc] as Record<string, string>)[k]?.trim());
      expect(missing, `locale "${loc}" is missing: ${missing.join(', ')}`).toEqual([]);
    }
  });

  it('has no extra keys in a non-English locale', () => {
    const english = new Set(Object.keys(MESSAGES.en));
    for (const loc of LOCALES.filter((l) => l !== 'en')) {
      const extra = Object.keys(MESSAGES[loc]).filter((k) => !english.has(k));
      expect(extra, `locale "${loc}" has stale keys: ${extra.join(', ')}`).toEqual([]);
    }
  });

  it('actually translates — Vietnamese differs from English on visible copy', () => {
    // Guards against a locale that was stubbed out by copying the English file.
    const sampled = ['nav.signIn', 'hero.title', 'pricing.title', 'faq.q1'] as const;
    for (const key of sampled) {
      expect(MESSAGES.vi[key]).not.toBe(MESSAGES.en[key]);
    }
  });
});

describe('detectLocale', () => {
  it('prefers an explicit stored choice', () => {
    expect(detectLocale('vi', ['en-GB'])).toBe('vi');
    expect(detectLocale('en', ['vi-VN'])).toBe('en');
  });

  it('falls back to the browser language, matching the primary subtag', () => {
    expect(detectLocale(null, ['vi-VN'])).toBe('vi');
    expect(detectLocale(null, ['en-US'])).toBe('en');
  });

  it('skips unsupported languages and keeps looking', () => {
    expect(detectLocale(null, ['fr-FR', 'de', 'vi'])).toBe('vi');
  });

  it('defaults to English when nothing matches', () => {
    expect(detectLocale(null, ['fr-FR'])).toBe('en');
    expect(detectLocale(null, [])).toBe('en');
    expect(detectLocale('klingon', [])).toBe('en');
  });
});

describe('isLocale', () => {
  it('accepts only supported locales', () => {
    expect(isLocale('en')).toBe(true);
    expect(isLocale('vi')).toBe(true);
    expect(isLocale('fr')).toBe(false);
    expect(isLocale(null)).toBe(false);
    expect(isLocale(42)).toBe(false);
  });
});

describe('store', () => {
  it('translates through the current locale', () => {
    const i18n = useI18nStore();
    i18n.setLocale('en');
    expect(i18n.t('nav.signIn')).toBe(MESSAGES.en['nav.signIn']);
    i18n.setLocale('vi');
    expect(i18n.t('nav.signIn')).toBe(MESSAGES.vi['nav.signIn']);
  });

  it('cycles locales with toggleLocale', () => {
    const i18n = useI18nStore();
    i18n.setLocale('en');
    i18n.toggleLocale();
    expect(i18n.locale).toBe('vi');
    i18n.toggleLocale();
    expect(i18n.locale).toBe('en');
  });
});
