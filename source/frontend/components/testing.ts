/**
 * Shared helpers for component tests.
 *
 * Not a `.test.ts` file, so Vitest does not try to collect it.
 */
import { mount } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import type { Component } from 'vue';

/**
 * Stub every lucide icon with an inert <svg>.
 *
 * The real icons render fine, but there are dozens per page and none of them
 * carry behaviour worth asserting — stubbing keeps the tests fast and stops an
 * icon rename from breaking an unrelated test.
 */
export const iconStub = { template: '<svg />' };

export function stubIcons(names: string[]) {
  return Object.fromEntries(names.map((n) => [n, iconStub]));
}

/** Icons used across the components under test. */
export const ICON_NAMES = [
  'X', 'LogIn', 'UserPlus', 'AlertCircle', 'Loader2', 'Check', 'Save', 'LogOut',
  'ArrowLeft', 'ArrowRight', 'Mail', 'Wrench', 'Shield', 'UserIcon', 'User',
  'CalendarDays', 'FolderKanban', 'Sun', 'Moon', 'Menu', 'Globe', 'ChevronDown',
  'PlayCircle', 'Keyboard', 'GitFork', 'Sparkles', 'WifiOff', 'Users', 'Gauge',
  'Trash2', 'LayoutGrid',
];

/**
 * Mount with a fresh Pinia.
 *
 * `setup` runs after the store exists but *before* mount, which matters for
 * components that read store state during `onMounted` — setting it afterwards
 * would be overwritten by the component's own initialisation.
 */
export function mountWithPinia(
  component: Component,
  // Loosely typed on purpose: `mount`'s generic mounting-options type is
  // resolved per-component, and threading it through a wrapper adds noise to
  // every call site for no safety a test would actually benefit from.
  options: Record<string, any> & { setup?: () => void } = {},
) {
  const { setup, ...mountOptions } = options;
  setActivePinia(createPinia());
  setup?.();
  // `setup` must not reach mount(): Vue would treat it as a component option.
  return mount(component as any, {
    ...mountOptions,
    global: {
      ...(mountOptions.global ?? {}),
      stubs: { ...stubIcons(ICON_NAMES), ...(mountOptions.global?.stubs ?? {}) },
    },
  });
}

/** A user object shaped like the API's UserProfile. */
export const fakeUser = (over: Record<string, unknown> = {}) => ({
  id: 1,
  email: 'ada@example.com',
  full_name: 'Ada Lovelace',
  skills: 'python,vue',
  avatar_url: null,
  created_at: '2026-01-15T10:00:00Z',
  ...over,
});

/** A project object shaped like the API's Project. */
export const fakeProject = (over: Record<string, unknown> = {}) => ({
  id: 1,
  name: 'Apollo',
  description: '',
  owner_id: 1,
  created_at: '2026-01-15T10:00:00Z',
  my_role: 'PM' as const,
  member_count: 1,
  ...over,
});
