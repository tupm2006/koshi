/**
 * Vitest setup, applied to every test file.
 *
 * jsdom does not implement `matchMedia`, which `themeStore` calls to read the
 * OS colour-scheme preference. Providing an inert stub keeps that a test-harness
 * concern rather than something the component has to defend against.
 */
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}
