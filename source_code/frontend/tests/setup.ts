import 'fake-indexeddb/auto';
import { beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

beforeEach(() => {
  setActivePinia(createPinia());
  // Clear localStorage before each test
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.clear();
  }
});
