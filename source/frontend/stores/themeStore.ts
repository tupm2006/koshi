import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export type ThemeMode = 'dark' | 'light' | 'system';

export const useThemeStore = defineStore('themeStore', () => {
  const storedTheme = (typeof window !== 'undefined' ? localStorage.getItem('koshi-theme') : null) as ThemeMode | null;
  const themeMode = ref<ThemeMode>(storedTheme || 'system');

  const resolvedTheme = computed<'dark' | 'light'>(() => {
    if (themeMode.value === 'system') {
      if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
      return 'light';
    }
    return themeMode.value;
  });

  const isDark = computed(() => resolvedTheme.value === 'dark');

  function applyTheme() {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;

    // 1. Inject temporary style to kill transitions on all elements
    const css = document.createElement('style');
    css.appendChild(
      document.createTextNode(
        `*, *::before, *::after {
          -webkit-transition: none !important;
          -moz-transition: none !important;
          -o-transition: none !important;
          -ms-transition: none !important;
          transition: none !important;
        }`
      )
    );
    document.head.appendChild(css);

    // 2. Toggle class
    if (resolvedTheme.value === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // 3. Force reflow to commit layout instantly
    void window.getComputedStyle(css).opacity;

    // 4. Remove freeze rule
    document.head.removeChild(css);
  }

  function setTheme(mode: ThemeMode) {
    themeMode.value = mode;
    if (typeof window !== 'undefined') {
      localStorage.setItem('koshi-theme', mode);
    }
    applyTheme();
  }

  function toggleTheme() {
    const nextMode: ThemeMode = isDark.value ? 'light' : 'dark';
    setTheme(nextMode);
  }

  function init() {
    applyTheme();
    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = () => {
        if (themeMode.value === 'system') {
          applyTheme();
        }
      };
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', listener);
      } else {
        (mediaQuery as any).addListener(listener);
      }
    }
  }

  return {
    themeMode,
    resolvedTheme,
    isDark,
    setTheme,
    toggleTheme,
    applyTheme,
    init,
  };
});

export function useTheme() {
  return useThemeStore();
}
