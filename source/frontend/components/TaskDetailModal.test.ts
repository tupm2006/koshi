// @vitest-environment jsdom
/**
 * Tests for the task detail inspector (D5 GAP-12).
 *
 * The largest component in the repo, and the only one with its own keyboard
 * mode: the global dispatcher steps aside while it is open, so `i` and
 * `Escape` are handled here instead (see `lib/keyboard.ts`).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

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

import TaskDetailModal from './TaskDetailModal.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeProject } from './testing';

function open(seed: (s: ReturnType<typeof useTaskStore>) => void = () => {}) {
  let store!: ReturnType<typeof useTaskStore>;
  let taskId = '';

  const w = mountWithPinia(TaskDetailModal, {
    props: { taskId: '' },
    setup: () => {
      store = useTaskStore();
      store.currentUser = { id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any;
      store.projects = [fakeProject()] as any;
      store.currentProjectId = 1;
      store.isBackendConnected = true;

      const created = store.createTask('Design the schema', 'HIGH')!;
      taskId = created.id;
      seed(store);
    },
  });

  w.setProps({ taskId });
  return { w, store, taskId };
}

const press = (w: any, key: string) =>
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));

beforeEach(() => vi.clearAllMocks());

describe('view mode', () => {
  it('shows the task title and its display key', async () => {
    const { w, taskId } = open();
    await w.vm.$nextTick();

    expect(w.text()).toContain('Design the schema');
    expect(w.text()).toContain(taskId);
  });

  it('renders no edit fields until edit mode is entered', async () => {
    const { w } = open();
    await w.vm.$nextTick();

    expect(w.find('input[type="text"]').exists()).toBe(false);
    expect(w.find('textarea').exists()).toBe(false);
  });

  it('shows a blocking reason when the task is blocked', async () => {
    const { w, store, taskId } = open();
    store.updateTask(taskId, { status: 'BLOCKED', blockingReason: 'Waiting on API keys' });
    await w.vm.$nextTick();

    expect(w.text()).toContain('Waiting on API keys');
  });

  it('reflects a task changed underneath it', async () => {
    const { w, store, taskId } = open();
    store.updateTask(taskId, { title: 'Renamed elsewhere' });
    await w.vm.$nextTick();

    expect(w.text()).toContain('Renamed elsewhere');
  });
});

describe('its own keyboard mode', () => {
  it('i enters edit mode', async () => {
    const { w } = open();
    await w.vm.$nextTick();

    press(w, 'i');
    await w.vm.$nextTick();

    expect(w.find('input[type="text"]').exists()).toBe(true);
  });

  it('Escape in view mode closes the inspector', async () => {
    const { w } = open();
    await w.vm.$nextTick();

    press(w, 'Escape');
    expect(w.emitted('close')).toBeTruthy();
  });

  it('Escape in edit mode saves and returns to view mode without closing', async () => {
    const { w, store, taskId } = open();
    await w.vm.$nextTick();

    press(w, 'i');
    await w.vm.$nextTick();
    await w.find('input[type="text"]').setValue('Renamed while editing');

    press(w, 'Escape');
    await w.vm.$nextTick();

    expect(store.tasks.find((t) => t.id === taskId)!.title).toBe('Renamed while editing');
    expect(w.find('input[type="text"]').exists()).toBe(false); // back to view mode
    expect(w.emitted('close')).toBeFalsy();                    // and still open
  });
});

describe('editing', () => {
  it('prefills the buffers from the task', async () => {
    const { w } = open();
    await w.vm.$nextTick();
    press(w, 'i');
    await w.vm.$nextTick();

    expect((w.find('input[type="text"]').element as HTMLInputElement).value)
      .toBe('Design the schema');
  });

  it('persists a status change through the store', async () => {
    const { w, store, taskId } = open();
    await w.vm.$nextTick();
    press(w, 'i');
    await w.vm.$nextTick();

    const statusSelect = w.findAll('select')[0]!;
    await statusSelect.setValue('DONE');
    await w.vm.$nextTick();

    expect(store.tasks.find((t) => t.id === taskId)!.status).toBe('DONE');
  });

  it('refuses to blank the title', async () => {
    const { w, store, taskId } = open();
    await w.vm.$nextTick();
    press(w, 'i');
    await w.vm.$nextTick();

    await w.find('input[type="text"]').setValue('   ');
    press(w, 'Escape');
    await w.vm.$nextTick();

    expect(store.tasks.find((t) => t.id === taskId)!.title).toBe('Design the schema');
  });

  it('resets to view mode when a different task is inspected', async () => {
    const { w, store } = open();
    await w.vm.$nextTick();
    press(w, 'i');
    await w.vm.$nextTick();
    expect(w.find('input[type="text"]').exists()).toBe(true);

    const other = store.createTask('Another task')!;
    await w.setProps({ taskId: other.id });
    await w.vm.$nextTick();

    expect(w.find('input[type="text"]').exists()).toBe(false);
    expect(w.text()).toContain('Another task');
  });
});

describe('read-only projects', () => {
  it('cannot change a task while a shared project is offline', async () => {
    // INV-15: the store gate applies here too — the inspector is not a
    // back door around the offline write policy.
    const { w, store, taskId } = open((s) => {
      s.projects = [fakeProject({ member_count: 4 })] as any;
    });
    await w.vm.$nextTick();

    press(w, 'i');
    await w.vm.$nextTick();

    // Go offline BEFORE typing: the inspector auto-saves on every field change,
    // so anything typed while still connected would legitimately persist.
    store.isBackendConnected = false;

    await w.find('input[type="text"]').setValue('Should not persist');
    press(w, 'Escape');
    await w.vm.$nextTick();

    expect(store.tasks.find((t) => t.id === taskId)!.title).toBe('Design the schema');
  });
});

describe('missing task', () => {
  it('renders nothing rather than throwing when the id does not resolve', async () => {
    const { w } = open();
    await w.setProps({ taskId: 'TSK-does-not-exist' });
    await w.vm.$nextTick();

    expect(w.text()).not.toContain('Design the schema');
  });
});
