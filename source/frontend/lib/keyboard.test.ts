// @vitest-environment jsdom
/**
 * Tests for the keyboard dispatcher (D5 GAP-12).
 *
 * This one file carries all fourteen FR-INT requirements, and until now every
 * one of them rested on manual verification. The bindings are also the thing
 * most likely to be "corrected" by someone trusting stale documentation — see
 * D7 / DEC-005, where `c` and `n` diverged for weeks.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    createTask: vi.fn(async () => ({})),
    updateTask: vi.fn(async () => ({})),
    deleteTask: vi.fn(async () => undefined),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import { createKeyboardHandler, isInputActive } from './keyboard';
import { useTaskStore } from '../stores/taskStore';
import { useThemeStore } from '../stores/themeStore';

const callbacks = () => ({
  onOpenQuickCreate: vi.fn(),
  onOpenAIDecomposer: vi.fn(),
  onOpenGitDiff: vi.fn(),
  onOpenDAG: vi.fn(),
  onOpenShortcutsHelp: vi.fn(),
  onFocusSearch: vi.fn(),
});

let cb: ReturnType<typeof callbacks>;
let handler: ReturnType<typeof createKeyboardHandler>;

/** Dispatch a keydown on window, optionally from a specific element. */
function press(key: string, opts: KeyboardEventInit & { target?: HTMLElement } = {}) {
  const { target, ...init } = opts;
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
  (target ?? window).dispatchEvent(event);
  return event;
}

/** Seed a board with three tasks the dispatcher can act on. */
function seedBoard(viewMode: 'TABLE' | 'KANBAN' = 'TABLE') {
  const store = useTaskStore();
  store.currentUser = { id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any;
  store.projects = [{
    id: 1, name: 'P', description: '', owner_id: 1,
    created_at: '2026-01-01T00:00:00Z', my_role: 'PM', member_count: 1,
  }] as any;
  store.currentProjectId = 1;
  store.isBackendConnected = true;
  store.viewMode = viewMode;

  store.createTask('First', 'LOW');
  store.createTask('Second', 'LOW');
  store.createTask('Third', 'LOW');
  store.selectedIndex = 0;
  return store;
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  cb = callbacks();
  handler = createKeyboardHandler(cb);
  handler.mount();
});

afterEach(() => {
  handler.unmount();
  document.body.innerHTML = '';
});

// ---------------------------------------------------------------------------
// isInputActive (FR-INT-10)
// ---------------------------------------------------------------------------

describe('isInputActive', () => {
  it.each(['INPUT', 'TEXTAREA', 'SELECT'])('treats <%s> as an active input', (tag) => {
    expect(isInputActive(document.createElement(tag))).toBe(true);
  });

  it('treats a contenteditable element as an active input', () => {
    const el = document.createElement('div');
    el.contentEditable = 'true';
    // jsdom does not derive isContentEditable from the attribute.
    Object.defineProperty(el, 'isContentEditable', { value: true });
    expect(isInputActive(el)).toBe(true);
  });

  it('treats an ordinary element as not an input', () => {
    expect(isInputActive(document.createElement('div'))).toBe(false);
  });

  it('handles null and non-elements without throwing', () => {
    expect(isInputActive(null)).toBe(false);
    expect(isInputActive({} as EventTarget)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Input guards (FR-INT-10)
// ---------------------------------------------------------------------------

describe('typing in an input', () => {
  it('does not trigger any shortcut', () => {
    const store = seedBoard();
    const input = document.createElement('input');
    document.body.appendChild(input);

    const before = store.viewMode;
    for (const key of ['b', 'n', 'd', '/', 'a', 'v', ' ']) {
      press(key, { target: input });
    }

    expect(store.viewMode).toBe(before);
    expect(store.tasks).toHaveLength(3);
    expect(cb.onOpenQuickCreate).not.toHaveBeenCalled();
    expect(cb.onFocusSearch).not.toHaveBeenCalled();
  });

  it('blurs the input on Escape', () => {
    seedBoard();
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    expect(document.activeElement).toBe(input);

    press('Escape', { target: input });
    expect(document.activeElement).not.toBe(input);
  });
});

// ---------------------------------------------------------------------------
// Escape and modal deference (FR-INT-11)
// ---------------------------------------------------------------------------

describe('Escape', () => {
  it('cancels an inline edit', () => {
    const store = seedBoard();
    store.startEditing(store.tasks[0]!.id);
    expect(store.editingTaskId).not.toBeNull();

    press('Escape');
    expect(store.editingTaskId).toBeNull();
  });

  it('defers to the detail modal when one is open', () => {
    const store = seedBoard();
    store.startEditing(store.tasks[0]!.id);
    store.openDetail(store.tasks[0]!.id);

    press('Escape');
    // The modal owns its own Escape handling, so the dispatcher does nothing.
    expect(store.editingTaskId).not.toBeNull();
  });
});

describe('with the detail modal open', () => {
  it('ignores global shortcuts so the modal keeps its own keys', () => {
    const store = seedBoard();
    store.openDetail(store.tasks[0]!.id);
    const before = store.viewMode;

    press('b');
    press('n');
    press('d');

    expect(store.viewMode).toBe(before);
    expect(store.tasks).toHaveLength(3);
    expect(cb.onOpenQuickCreate).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// View toggle and theme (FR-INT-01, FR-INT-12)
// ---------------------------------------------------------------------------

describe('view and theme', () => {
  it('b toggles between table and kanban', () => {
    const store = seedBoard('TABLE');
    press('b');
    expect(store.viewMode).toBe('KANBAN');
    press('b');
    expect(store.viewMode).toBe('TABLE');
  });

  it('t toggles the theme', () => {
    seedBoard();
    const theme = useThemeStore();
    const spy = vi.spyOn(theme, 'toggleTheme');
    press('t');
    expect(spy).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Navigation (FR-INT-02, FR-INT-03)
// ---------------------------------------------------------------------------

describe('navigation in table view', () => {
  it('j and ArrowDown move down; k and ArrowUp move up', () => {
    const store = seedBoard('TABLE');

    press('j');
    expect(store.selectedIndex).toBe(1);
    press('ArrowDown');
    expect(store.selectedIndex).toBe(2);
    press('k');
    expect(store.selectedIndex).toBe(1);
    press('ArrowUp');
    expect(store.selectedIndex).toBe(0);
  });

  it('stays within bounds at both ends', () => {
    const store = seedBoard('TABLE');

    press('k');
    expect(store.selectedIndex).toBe(0);

    for (let i = 0; i < 10; i += 1) press('j');
    expect(store.selectedIndex).toBe(store.filteredTasks.length - 1);
  });

  it('ignores h and l, which are kanban-only', () => {
    const store = seedBoard('TABLE');
    const spy = vi.spyOn(store, 'moveKanbanCursor');

    press('h');
    press('l');
    press('ArrowLeft');
    press('ArrowRight');

    expect(spy).not.toHaveBeenCalled();
  });
});

describe('navigation in kanban view', () => {
  it('routes all four directions to the 2D cursor', () => {
    const store = seedBoard('KANBAN');
    const spy = vi.spyOn(store, 'moveKanbanCursor');

    press('h'); press('l'); press('j'); press('k');
    expect(spy.mock.calls.map((c) => c[0])).toEqual(['left', 'right', 'down', 'up']);

    spy.mockClear();
    press('ArrowLeft'); press('ArrowRight'); press('ArrowDown'); press('ArrowUp');
    expect(spy.mock.calls.map((c) => c[0])).toEqual(['left', 'right', 'down', 'up']);
  });

  it('does not move the table cursor', () => {
    const store = seedBoard('KANBAN');
    const spy = vi.spyOn(store, 'selectNext');
    press('j');
    expect(spy).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Lateral shift (FR-INT-05)
// ---------------------------------------------------------------------------

describe('Shift+H / Shift+L', () => {
  it('shifts the active card across columns in kanban view', () => {
    const store = seedBoard('KANBAN');
    const spy = vi.spyOn(store, 'shiftActiveKanbanTask');

    press('H', { shiftKey: true });
    press('L', { shiftKey: true });

    expect(spy.mock.calls.map((c) => c[0])).toEqual(['left', 'right']);
  });

  it('does nothing in table view', () => {
    const store = seedBoard('TABLE');
    const spy = vi.spyOn(store, 'shiftActiveKanbanTask');

    press('H', { shiftKey: true });
    press('L', { shiftKey: true });

    expect(spy).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Task actions (FR-INT-04, 06, 07, 08)
// ---------------------------------------------------------------------------

describe('task actions', () => {
  it('Space cycles the selected task status', () => {
    const store = seedBoard('TABLE');
    const id = store.filteredTasks[0]!.id;
    expect(store.tasks.find((t) => t.id === id)!.status).toBe('TODO');

    press(' ');
    expect(store.tasks.find((t) => t.id === id)!.status).toBe('IN_PROGRESS');
  });

  it('Enter opens the detail inspector, not an inline edit', () => {
    const store = seedBoard('TABLE');
    press('Enter');

    expect(store.activeDetailTaskId).toBe(store.filteredTasks[0]!.id);
    expect(store.editingTaskId).toBeNull();
  });

  it('i starts an inline edit, not the inspector', () => {
    // DEC-005: the retired docs had these two swapped.
    const store = seedBoard('TABLE');
    press('i');

    expect(store.editingTaskId).toBe(store.filteredTasks[0]!.id);
    expect(store.activeDetailTaskId).toBeNull();
  });

  it('n opens the create modal — not c', () => {
    seedBoard();
    press('c');
    expect(cb.onOpenQuickCreate).not.toHaveBeenCalled();

    press('n');
    expect(cb.onOpenQuickCreate).toHaveBeenCalledTimes(1);
  });

  it('d and Backspace delete the selected task', () => {
    const store = seedBoard('TABLE');
    press('d');
    expect(store.tasks).toHaveLength(2);
    press('Backspace');
    expect(store.tasks).toHaveLength(1);
  });

  it('leaves Cmd/Ctrl+Backspace to the browser', () => {
    const store = seedBoard('TABLE');
    press('Backspace', { metaKey: true });
    press('Backspace', { ctrlKey: true });
    expect(store.tasks).toHaveLength(3);
  });

  it.each([
    ['1', 'LOW'],
    ['2', 'MEDIUM'],
    ['3', 'HIGH'],
    ['4', 'CRITICAL'],
  ])('%s sets priority %s', (key, priority) => {
    const store = seedBoard('TABLE');
    const id = store.filteredTasks[0]!.id;

    press(key);
    expect(store.tasks.find((t) => t.id === id)!.priority).toBe(priority);
  });
});

// ---------------------------------------------------------------------------
// Callback shortcuts (FR-INT-09, 13)
// ---------------------------------------------------------------------------

describe('shortcuts that open a panel', () => {
  it.each([
    ['/', 'onFocusSearch'],
    ['a', 'onOpenAIDecomposer'],
    ['g', 'onOpenGitDiff'],
    ['v', 'onOpenDAG'],
    ['?', 'onOpenShortcutsHelp'],
  ] as const)('%s calls %s', (key, name) => {
    seedBoard();
    press(key);
    expect(cb[name]).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// preventDefault and lifecycle
// ---------------------------------------------------------------------------

describe('event handling', () => {
  it('prevents the browser default for keys it consumes', () => {
    seedBoard('TABLE');
    for (const key of ['b', 'j', 'k', ' ', 'n', '/', 'a', 'g', 'v', '?']) {
      expect(press(key).defaultPrevented, `${key} should be consumed`).toBe(true);
    }
  });

  it('leaves unbound keys alone', () => {
    seedBoard('TABLE');
    for (const key of ['q', 'z', 'F5']) {
      expect(press(key).defaultPrevented, `${key} should pass through`).toBe(false);
    }
  });

  it('stops responding after unmount', () => {
    const store = seedBoard('TABLE');
    handler.unmount();

    press('b');
    press('n');

    expect(store.viewMode).toBe('TABLE');
    expect(cb.onOpenQuickCreate).not.toHaveBeenCalled();

    handler.mount(); // so afterEach unmount stays symmetric
  });
});
