// @vitest-environment jsdom
/**
 * The notification feed.
 *
 * The rules that make a feed worth opening are in the store and the server; the
 * page's job is to render an event as a readable line without inventing
 * anything, and to take you to the thing it is about.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    fetchBlob: vi.fn(async () => new Blob(['x'], { type: 'image/png' })),
    listProjects: vi.fn(async () => [] as any[]),
    listMembers: vi.fn(async () => [] as any[]),
    listInvitations: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    createTask: vi.fn(async () => ({})),
    updateTask: vi.fn(async () => ({})),
    deleteTask: vi.fn(async () => undefined),
    listNotifications: vi.fn(async () => [] as any[]),
    unreadNotificationCount: vi.fn(async () => 0),
    markNotificationRead: vi.fn(async () => ({})),
    markAllNotificationsRead: vi.fn(async () => undefined),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import NotificationsPage from './NotificationsPage.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeProject } from './testing';

type Store = ReturnType<typeof useTaskStore>;

const note = (over: Record<string, unknown> = {}) => ({
  id: 1,
  kind: 'MENTION',
  actor: { id: 2, full_name: 'Grace Hopper', email: 'g@navy.mil', skills: '' },
  project_id: 1,
  project_name: 'Apollo',
  task_id: 7,
  task_key: 'TSK-7',
  task_title: 'Ship the parser',
  comment_id: 3,
  excerpt: 'hey @[Ada](1) can you look',
  read_at: null,
  created_at: new Date().toISOString(),
  ...over,
});

function open(seed: (s: Store) => void = () => {}) {
  let store!: Store;
  const w = mountWithPinia(NotificationsPage, {
    setup: () => {
      store = useTaskStore();
      store.currentUser = { id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any;
      store.projects = [fakeProject()] as any;
      store.currentProjectId = 1;
      store.isBackendConnected = true;
      seed(store);
    },
  });
  return { w, store };
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.listNotifications.mockResolvedValue([]);
  apiMock.unreadNotificationCount.mockResolvedValue(0);
});

describe('rendering the feed', () => {
  it('says plainly that your own comments never appear here', () => {
    const { w } = open();
    expect(w.find('#notifications-empty').text()).toMatch(/never about your own/i);
  });

  it('renders who did what to which task', () => {
    const { w } = open((s) => { s.notifications = [note()] as any; });
    const text = w.find('[data-notification="1"]').text();

    expect(text).toContain('Grace Hopper');
    expect(text).toContain('mentioned you in');
    expect(text).toContain('Ship the parser');
    expect(text).toContain('TSK-7');
  });

  it('renders a mention token in the excerpt as a readable name', () => {
    // The excerpt is raw comment text; showing `@[Ada](1)` in the feed would be
    // leaking the storage format at the reader.
    const { w } = open((s) => { s.notifications = [note()] as any; });
    const text = w.find('[data-notification="1"]').text();

    expect(text).toContain('@Ada');
    expect(text).not.toContain('@[Ada](1)');
  });

  it('uses a different verb for a reply', () => {
    // Driven entirely by `kind` — no message is stored server-side, because
    // wording belongs to whoever knows the reader's language.
    const { w } = open((s) => { s.notifications = [note({ kind: 'REPLY' })] as any; });
    expect(w.find('[data-notification="1"]').text()).toContain('replied to you on');
  });

  it('has a label for every kind the server can send', () => {
    // Adding a kind must not render as a blank line.
    const kinds = ['MENTION', 'REPLY', 'TASK_ASSIGNED', 'PROJECT_INVITED', 'TASK_DUE_SOON'];
    const { w } = open((s) => {
      s.notifications = kinds.map((k, i) => note({ id: i + 1, kind: k })) as any;
    });

    for (const k of kinds) {
      const el = w.find(`[data-kind="${k}"]`);
      expect(el.exists(), k).toBe(true);
      expect(el.text().length, k).toBeGreaterThan(10);
    }
  });

  it('marks unread entries visibly', () => {
    const { w } = open((s) => {
      s.notifications = [note({ id: 1 }), note({ id: 2, read_at: '2026-08-29T00:00:00Z' })] as any;
    });

    expect(w.find('[data-notification="1"]').attributes('data-unread')).toBe('true');
    expect(w.find('[data-notification="2"]').attributes('data-unread')).toBe('false');
    expect(w.findAll('[data-unread-dot]')).toHaveLength(1);
  });

  it('offers "mark all" only when something is unread', () => {
    const read = open((s) => { s.notifications = [note({ read_at: '2026-08-29T00:00:00Z' })] as any; });
    expect(read.w.find('#notifications-read-all').exists()).toBe(false);

    const unread = open((s) => { s.notifications = [note()] as any; });
    expect(unread.w.find('#notifications-read-all').exists()).toBe(true);
  });
});

describe('acting on a notification', () => {
  it('marks it read and opens its task', async () => {
    const { w, store } = open((s) => { s.notifications = [note()] as any; });

    await w.find('[data-notification="1"]').trigger('click');
    await flushPromises();

    expect(apiMock.markNotificationRead).toHaveBeenCalledWith(1);
    expect(store.appView).toBe('BOARD');
  });

  it('drops the badge immediately rather than waiting on the server', async () => {
    // Optimistic: the count should fall the moment it is clicked. The call is
    // idempotent, so a failure leaves it merely stale.
    const { w, store } = open((s) => {
      s.notifications = [note()] as any;
      s.unreadCount = 1;
    });

    await w.find('[data-notification="1"]').trigger('click');
    expect(store.unreadCount).toBe(0);
  });

  it('switches project when the task is in another one', async () => {
    const { w, store } = open((s) => {
      s.currentProjectId = 1;
      s.projects = [fakeProject({ id: 1 }), fakeProject({ id: 5 })] as any;
      s.notifications = [note({ project_id: 5 })] as any;
    });

    await w.find('[data-notification="1"]').trigger('click');
    await flushPromises();

    // A notification is most useful precisely when it points somewhere else.
    expect(store.currentProjectId).toBe(5);
  });

  it('mark-all clears every entry and the badge', async () => {
    const { w, store } = open((s) => {
      s.notifications = [note({ id: 1 }), note({ id: 2 })] as any;
      s.unreadCount = 2;
    });

    await w.find('#notifications-read-all').trigger('click');
    await flushPromises();

    expect(apiMock.markAllNotificationsRead).toHaveBeenCalled();
    expect(store.unreadCount).toBe(0);
    expect(w.findAll('[data-unread-dot]')).toHaveLength(0);
  });

  it('goes back to the board', async () => {
    const { w, store } = open();
    await w.find('#notifications-back').trigger('click');
    expect(store.appView).toBe('BOARD');
  });
});

describe('the store rules', () => {
  it('does not re-mark something already read', async () => {
    const { store } = open((s) => {
      s.notifications = [note({ read_at: '2026-08-29T00:00:00Z' })] as any;
    });

    await store.markNotificationRead(1);
    expect(apiMock.markNotificationRead).not.toHaveBeenCalled();
  });

  it('never lets the badge go negative', async () => {
    const { store } = open((s) => {
      s.notifications = [note()] as any;
      s.unreadCount = 0;  // out of step with the feed, e.g. after a stale load
    });

    await store.markNotificationRead(1);
    expect(store.unreadCount).toBe(0);
  });

  it('clears the feed on sign-out', async () => {
    const { store } = open((s) => {
      s.notifications = [note()] as any;
      s.unreadCount = 1;
    });

    await store.logout();

    expect(store.notifications).toEqual([]);
    expect(store.unreadCount).toBe(0);
  });

  it('survives a feed that fails to load', async () => {
    apiMock.listNotifications.mockRejectedValue(new Error('down'));
    const { store } = open();

    await store.loadNotifications();

    expect(store.notifications).toEqual([]);
  });
});
