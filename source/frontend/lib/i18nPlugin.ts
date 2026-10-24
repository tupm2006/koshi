/**
 * `$t` in every template, so a component needs no imports to be translatable.
 * Reads the Pinia store at render time, which makes it reactive: switching
 * locale re-renders every component that called it.
 */
import type { App } from 'vue';
import { useI18nStore } from '../stores/i18nStore';
import type { TranslationKey } from './translations';
import type { DueWords } from './urgency';

/** `{name}` placeholders, filled from `vars`. */
export function format(text: string, vars?: Record<string, string | number>): string {
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
}

export function tr(key: TranslationKey, vars?: Record<string, string | number>): string {
  return format(useI18nStore().t(key), vars);
}

export const i18nPlugin = {
  install(app: App) {
    app.config.globalProperties.$t = tr;
  },
};

declare module 'vue' {
  interface ComponentCustomProperties {
    $t: typeof tr;
  }
}

/** Localised phrases for `dueLabel`. */
export function dueWords(): DueWords {
  return {
    done: tr('due.done'), today: tr('due.today'), tomorrow: tr('due.tomorrow'),
    overdue: (n) => tr('due.overdue', { n }), inDays: (n) => tr('due.inDays', { n }),
  };
}

/** BCP-47 tag for dates, following the UI language rather than the browser's. */
export function uiLocale(): string {
  return useI18nStore().locale === 'vi' ? 'vi-VN' : 'en-GB';
}
