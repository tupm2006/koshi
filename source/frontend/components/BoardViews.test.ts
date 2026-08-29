// @vitest-environment jsdom
/**
 * Tests for the two board views (D5 GAP-12).
 *
 * These render the task data users actually work with, so the assertions focus
 * on what the board must never get wrong: showing tasks from the selected
 * project, honouring filters, reflecting the selection the keyboard moves, and
 * putting each card in the right status column.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    // <img> cannot send a bearer token, so media is fetched (F-45).
    fetchBlob: vi.fn(async () => new Blob(['x'], { type: 'image/png' })),
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

import TaskTable from './TaskTable.vue';
import KanbanBoard from './KanbanBoard.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeProject } from './testing';

const onOpenCreate = vi.fn();

/** Seed the store, then mount — the views read state during render. */
function board(component: any, seed: (s: ReturnType<typeof useTaskStore>) => void = () => {}) {
  let store!: ReturnType<typeof useTaskStore>;
  const w = mountWithPinia(component, {
    props: { onOpenCreate },
    setup: () => {
      store = useTaskStore();
      store.currentUser = { id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any;
      store.projects = [fakeProject()] as any;
      store.currentProjectId = 1;
      store.isBackendConnected = true;

      store.createTask('Write the parser', 'HIGH');
      store.createTask('Fix the migration', 'LOW');
      store.createTask('Ship the dashboard', 'CRITICAL');
      store.selectedIndex = 0;
      seed(store);
    },
  });
  return { w, store };
}

beforeEach(() => {
  vi.clearAllMocks();
  onOpenCreate.mockClear();
});

// ---------------------------------------------------------------------------
// TaskTable
// ---------------------------------------------------------------------------

describe('TaskTable', () => {
  it('renders every task in the current project', () => {
    const { w } = board(TaskTable);
    const text = w.text();
    expect(text).toContain('Write the parser');
    expect(text).toContain('Fix the migration');
    expect(text).toContain('Ship the dashboard');
  });

  it('shows the display key, not the raw server id', () => {
    // INV-14: "TSK-n" is the label; the integer id stays internal.
    const { w, store } = board(TaskTable);
    expect(w.text()).toContain(store.tasks[0]!.id);
    expect(store.tasks[0]!.id).toMatch(/^TSK-/);
  });

  it('honours the search filter', async () => {
    const { w, store } = board(TaskTable);
    store.setSearchQuery('parser');
    await w.vm.$nextTick();

    expect(w.text()).toContain('Write the parser');
    expect(w.text()).not.toContain('Fix the migration');
  });

  it('honours the status filter', async () => {
    const { w, store } = board(TaskTable);
    store.setStatus(store.tasks[0]!.id, 'DONE');
    store.setFilterStatus('DONE');
    await w.vm.$nextTick();

    expect(w.text()).toContain(store.tasks.find((t) => t.status === 'DONE')!.title);
    expect(w.text()).not.toContain('Fix the migration');
  });

  it('marks exactly one row as selected, and follows the selection', async () => {
    const { w, store } = board(TaskTable);
    const selected = () => w.findAll('[data-selected="true"]');

    expect(selected()).toHaveLength(1);
    const first = selected()[0]!.text();

    store.selectNext();
    await w.vm.$nextTick();

    expect(selected()).toHaveLength(1);
    expect(selected()[0]!.text()).not.toBe(first);
  });

  it('renders an edit input only for the row being edited', async () => {
    const { w, store } = board(TaskTable);
    expect(w.find('input').exists()).toBe(false);

    store.startEditing(store.tasks[0]!.id);
    await w.vm.$nextTick();

    // Two inputs, not one: the table renders separate desktop and mobile
    // layouts and both are in the DOM, with CSS deciding which is visible.
    // Asserting the real number rather than the tidy one.
    const inputs = w.findAll('input');
    expect(inputs).toHaveLength(2);

    // Crucially, they belong to the edited row alone.
    const editedRow = w.find(`[data-task="${store.tasks[0]!.id}"]`);
    expect(editedRow.findAll('input')).toHaveLength(2);
  });

  it('advertises the correct create shortcut in the empty state', async () => {
    // F-20: this panel still told users to press `c` long after the binding
    // moved to `n` (DEC-005).
    const { w, store } = board(TaskTable);
    store.tasks = [];
    await w.vm.$nextTick();

    const kbd = w.find('kbd');
    expect(kbd.text()).toBe('n');
  });

  it('invites the user to create a task when the board is empty', async () => {
    const { w, store } = board(TaskTable);
    store.tasks = [];
    await w.vm.$nextTick();

    const button = w.findAll('button').find((b) => /create task/i.test(b.text()));
    expect(button).toBeDefined();
    await button!.trigger('click');
    expect(onOpenCreate).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// KanbanBoard
// ---------------------------------------------------------------------------

describe('KanbanBoard', () => {
  it('renders exactly the four status columns, in cycle order', () => {
    // INV-01 / D4 §3.1 — the column order is the status cycle order.
    const { w } = board(KanbanBoard);
    const headings = w.findAll('[data-column]').map((c) => c.attributes('data-column'));
    expect(headings).toEqual(['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE']);
  });

  it('places each task in the column matching its status', async () => {
    const { w, store } = board(KanbanBoard);
    const target = store.tasks.find((t) => t.title === 'Fix the migration')!;
    store.setStatus(target.id, 'BLOCKED');
    await w.vm.$nextTick();

    const blocked = w.find('[data-column="BLOCKED"]');
    const todo = w.find('[data-column="TODO"]');
    expect(blocked.text()).toContain('Fix the migration');
    expect(todo.text()).not.toContain('Fix the migration');
  });

  it('moves a card between columns when its status cycles', async () => {
    const { w, store } = board(KanbanBoard);
    const id = store.tasks[0]!.id;
    const title = store.tasks[0]!.title;

    expect(w.find('[data-column="TODO"]').text()).toContain(title);

    store.cycleStatus(id);
    await w.vm.$nextTick();

    expect(w.find('[data-column="TODO"]').text()).not.toContain(title);
    expect(w.find('[data-column="IN_PROGRESS"]').text()).toContain(title);
  });

  it('counts the tasks in each column', async () => {
    const { w, store } = board(KanbanBoard);
    store.setStatus(store.tasks[0]!.id, 'DONE');
    await w.vm.$nextTick();

    expect(w.find('[data-column="DONE"]').text()).toContain('1');
  });

  it('honours the search filter', async () => {
    const { w, store } = board(KanbanBoard);
    store.setSearchQuery('dashboard');
    await w.vm.$nextTick();

    expect(w.text()).toContain('Ship the dashboard');
    expect(w.text()).not.toContain('Write the parser');
  });

  it('marks the active card and follows the kanban cursor', async () => {
    const { w, store } = board(KanbanBoard);
    const active = () => w.findAll('[data-active-card="true"]');

    expect(active()).toHaveLength(1);
    const first = active()[0]!.text();

    store.moveKanbanCursor('down');
    await w.vm.$nextTick();

    expect(active()).toHaveLength(1);
    expect(active()[0]!.text()).not.toBe(first);
  });

  it('shows the blocking reason on a blocked card', async () => {
    const { w, store } = board(KanbanBoard);
    const id = store.tasks[0]!.id;
    store.updateTask(id, { status: 'BLOCKED', blockingReason: 'Waiting on API keys' });
    await w.vm.$nextTick();

    expect(w.find('[data-column="BLOCKED"]').text()).toContain('Waiting on API keys');
  });
});
