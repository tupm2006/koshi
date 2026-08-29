/**
 * Tests for the Pinia store (D5 GAP-05).
 *
 * The store is the widest-blast-radius module in the repo: it owns task
 * mutations, project selection, the screen state machine, persistence ordering,
 * and every auth transition. All three DEC-012 defects lived here.
 *
 * `idb-keyval` and the API client are faked so the store can be exercised
 * without a browser or a server.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

// --- fakes -----------------------------------------------------------------

// vi.mock factories are hoisted above the file body, so anything they close
// over must be created with vi.hoisted().
const { idb, apiMock } = vi.hoisted(() => ({
  idb: new Map<string, unknown>(),
  apiMock: {
    getToken: vi.fn(() => null as string | null),
    logout: vi.fn(),
    getMe: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    createProject: vi.fn(),
    getTasks: vi.fn(async () => [] as any[]),
    createTask: vi.fn(async () => ({})),
    updateTask: vi.fn(async () => ({})),
    deleteTask: vi.fn(async () => undefined),
    updateProfile: vi.fn(),
    listInvitations: vi.fn(async () => [] as any[]),
    listMembers: vi.fn(async () => [] as any[]),
    acceptInvitation: vi.fn(),
    declineInvitation: vi.fn(async () => undefined),
  },
}));

vi.mock('idb-keyval', () => ({
  get: vi.fn(async (k: string) => idb.get(k)),
  set: vi.fn(async (k: string, v: unknown) => { idb.set(k, v); }),
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});

import { useTaskStore } from './taskStore';

const project = (over: Partial<any> = {}) => ({
  id: 1, name: 'P', description: '', owner_id: 1,
  created_at: '2026-01-01T00:00:00Z', my_role: 'PM', member_count: 1, ...over,
});

function store() {
  return useTaskStore();
}

beforeEach(() => {
  setActivePinia(createPinia());
  idb.clear();
  vi.clearAllMocks();
  apiMock.getToken.mockReturnValue(null);
  apiMock.listProjects.mockResolvedValue([]);
  apiMock.getTasks.mockResolvedValue([]);
});

// ---------------------------------------------------------------------------
// Screen state machine (FR-NAV)
// ---------------------------------------------------------------------------

describe('screen state', () => {
  it('starts on the landing page with no board data when there is no session', async () => {
    const s = store();
    await s.init();

    expect(s.appView).toBe('LANDING');
    expect(s.tasks).toEqual([]);
  });

  it('moves to the board on authentication', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);

    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    expect(s.appView).toBe('BOARD');
    expect(s.currentProjectId).toBe(1);
  });

  it('opens the dashboard when an authenticated account has no projects', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([]);

    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    expect(s.currentProjectId).toBeNull();
    expect(s.isDashboardOpen).toBe(true);
    expect(s.tasks).toEqual([]);
  });

  it('returns to the landing page on logout and clears session state', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    await s.logout();

    expect(s.appView).toBe('LANDING');
    expect(s.currentUser).toBeNull();
    expect(s.projects).toEqual([]);
    expect(s.currentProjectId).toBeNull();
    expect(s.tasks).toEqual([]);
    expect(apiMock.logout).toHaveBeenCalled();
  });

  it('navigates between board and profile', () => {
    const s = store();
    s.showProfile();
    expect(s.appView).toBe('PROFILE');
    s.showBoard();
    expect(s.appView).toBe('BOARD');
  });

  it('has no guest mode', () => {
    // Guest mode was removed deliberately; a signed-out visitor gets the
    // landing page and nothing else.
    expect((store() as any).continueAsGuest).toBeUndefined();
    expect((store() as any).isGuestMode).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Offline editing policy (FR-PERS-02)
// ---------------------------------------------------------------------------

describe('offline editing policy', () => {
  async function withProject(memberCount: number, connected: boolean) {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project({ member_count: memberCount })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);
    s.isBackendConnected = connected;
    return s;
  }

  it('allows editing a personal project while offline', async () => {
    const s = await withProject(1, false);

    expect(s.isPersonalProject).toBe(true);
    expect(s.canMutate).toBe(true);
    expect(s.isReadOnly).toBe(false);
    expect(s.readOnlyReason).toBeNull();
  });

  it('blocks editing a shared project while offline', async () => {
    const s = await withProject(3, false);

    expect(s.isPersonalProject).toBe(false);
    expect(s.canMutate).toBe(false);
    expect(s.readOnlyReason).toBe('OFFLINE_SHARED');
  });

  it('allows editing a shared project while connected', async () => {
    const s = await withProject(3, true);
    expect(s.canMutate).toBe(true);
  });

  it('refuses mutations on an offline shared project', async () => {
    const s = await withProject(3, true);
    const created = s.createTask('Real task');
    expect(created).not.toBeNull();
    const id = created!.id;

    s.isBackendConnected = false;

    expect(s.createTask('Blocked')).toBeNull();
    s.updateTask(id, { title: 'hijacked' });
    s.deleteTask(id);

    // Nothing changed: the task is still present and still named as created.
    expect(s.tasks).toHaveLength(1);
    expect(s.tasks[0]!.title).toBe('Real task');
  });

  it('still permits mutations on an offline personal project', async () => {
    const s = await withProject(1, false);

    const created = s.createTask('Offline note');
    expect(created).not.toBeNull();

    s.updateTask(created!.id, { title: 'Edited offline' });
    expect(s.tasks[0]!.title).toBe('Edited offline');
  });

  it('cannot mutate with no project selected', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    expect(s.canMutate).toBe(false);
    expect(s.readOnlyReason).toBe('NO_PROJECT');
    expect(s.createTask('Nope')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Project selection and cache partitioning (INV-12)
// ---------------------------------------------------------------------------

describe('project selection', () => {
  it('caches each project under its own IndexedDB key', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project({ id: 1 }), project({ id: 2 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    s.isBackendConnected = true;
    s.createTask('Task in project 1');
    await s.persist();

    await s.selectProject(2);
    s.createTask('Task in project 2');
    await s.persist();

    expect(idb.get('koshi_tasks_v2_p1')).toHaveLength(1);
    expect(idb.get('koshi_tasks_v2_p2')).toHaveLength(1);
    expect((idb.get('koshi_tasks_v2_p1') as any[])[0].title).toBe('Task in project 1');
    expect((idb.get('koshi_tasks_v2_p2') as any[])[0].title).toBe('Task in project 2');
  });

  it('resets the selection cursor when switching project', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project({ id: 1 }), project({ id: 2 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    s.selectedIndex = 5;
    s.kanbanColIndex = 3;
    await s.selectProject(2);

    expect(s.selectedIndex).toBe(0);
    expect(s.kanbanColIndex).toBe(0);
    expect(s.currentProjectId).toBe(2);
  });

  it('keeps a valid selection when reloading projects', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project({ id: 1 }), project({ id: 2 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);
    await s.selectProject(2);

    await s.loadProjects();
    expect(s.currentProjectId).toBe(2);
  });

  it('falls back to the first project when the selected one disappears', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project({ id: 1 }), project({ id: 2 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);
    await s.selectProject(2);

    apiMock.listProjects.mockResolvedValue([project({ id: 1 })]);
    await s.loadProjects();

    expect(s.currentProjectId).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Task id translation (INV-14)
// ---------------------------------------------------------------------------

describe('task id translation', () => {
  it('maps server integer ids and dependencies to display keys', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    apiMock.getTasks.mockResolvedValue([
      { id: 7, key: 'TSK-7', title: 'Dependent', status: 'TODO', priority: 'HIGH',
        complexity_points: 2, dependencies: [6], acceptance_criteria: [],
        created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
    ]);

    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);

    expect(s.tasks[0]!.id).toBe('TSK-7');
    expect(s.tasks[0]!.dependencies).toEqual(['TSK-6']);
  });

  it('sends dependencies back to the server as integer ids', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    apiMock.getTasks.mockResolvedValue([
      { id: 7, key: 'TSK-7', title: 'T', status: 'TODO', priority: 'HIGH',
        complexity_points: 2, dependencies: [], acceptance_criteria: [],
        created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
    ]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);
    s.isBackendConnected = true;

    s.updateTask('TSK-7', { dependencies: ['TSK-6', 'TSK-9'] } as any);

    expect(apiMock.updateTask).toHaveBeenCalledWith(7, expect.objectContaining({
      dependencies: [6, 9],
    }));
  });
});

// ---------------------------------------------------------------------------
// Status cycle (FR-DOM-02 / D4 §3.1)
// ---------------------------------------------------------------------------

describe('status cycle', () => {
  it('advances TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);
    s.isBackendConnected = true;

    const task = s.createTask('Cycle me')!;
    const seen = [task.status];
    for (let i = 0; i < 4; i += 1) {
      s.cycleStatus(task.id);
      seen.push(s.tasks.find((t) => t.id === task.id)!.status);
    }

    expect(seen).toEqual(['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'TODO']);
  });
});

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

describe('filters', () => {
  async function seeded() {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any);
    s.isBackendConnected = true;
    s.createTask('Write the parser', 'HIGH');
    s.createTask('Fix the migration', 'LOW');
    return s;
  }

  it('filters by search query, case-insensitively', async () => {
    const s = await seeded();
    s.setSearchQuery('PARSER');
    expect(s.filteredTasks.map((t) => t.title)).toEqual(['Write the parser']);
  });

  it('filters by status', async () => {
    const s = await seeded();
    const first = s.tasks[0]!;
    s.setStatus(first.id, 'DONE');

    s.setFilterStatus('DONE');
    expect(s.filteredTasks.every((t) => t.status === 'DONE')).toBe(true);

    s.setFilterStatus('ALL');
    expect(s.filteredTasks).toHaveLength(2);
  });

  it('filters by priority', async () => {
    const s = await seeded();
    s.setFilterPriority('HIGH');
    expect(s.filteredTasks.map((t) => t.priority)).toEqual(['HIGH']);
  });
});

// ---------------------------------------------------------------------------
// Deadlines, scope and invitations
// ---------------------------------------------------------------------------

const invitation = (over: Partial<any> = {}) => ({
  project_id: 7, project_name: 'Orion', project_description: '',
  role: 'MEMBER', invited_by_name: 'Ada', invited_at: null, ...over,
});

describe('creating a task with a deadline and an assignee', () => {
  async function ready(over: Partial<any> = {}) {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project(over)]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);
    s.isBackendConnected = true;
    return s;
  }

  it('stores a due date and sends it to the server', async () => {
    const s = await ready();
    apiMock.createTask.mockClear();

    const due = '2026-09-30T23:59:59.000Z';
    const t = s.createTask('Ship it', 'HIGH', 'TODO', {
      dueDate: due, assignees: [{ id: 4, full_name: 'Dev' }],
    })!;

    expect(t.dueDate).toBe(due);
    expect(apiMock.createTask).toHaveBeenCalledWith(
      expect.objectContaining({ due_date: due, assignee_ids: [4] }),
    );
  });

  it('sends null rather than an empty string when there is no deadline', async () => {
    // '' would be stored and then sort as an unparseable date.
    const s = await ready();
    apiMock.createTask.mockClear();

    const t = s.createTask('No deadline')!;

    expect(t.dueDate).toBeUndefined();
    expect(apiMock.createTask).toHaveBeenCalledWith(
      expect.objectContaining({ due_date: null, assignee_ids: [] }),
    );
  });
});

describe('board ordering', () => {
  it('puts an overdue task above a newer undated one', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);
    s.isBackendConnected = true;

    s.createTask('Undated but newest');
    const overdue = s.createTask('Overdue', 'LOW', 'TODO', {
      dueDate: new Date(Date.now() - 86_400_000 * 2).toISOString(),
    })!;

    // Creation order would have put the undated task first.
    expect(s.filteredTasks[0]!.id).toBe(overdue.id);
  });
});

describe('scope', () => {
  async function shared(role: 'PM' | 'MEMBER') {
    const s = store();
    apiMock.listProjects.mockResolvedValue([project({ my_role: role, member_count: 3 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);
    s.isBackendConnected = true;
    return s;
  }

  it('opens a PM on the whole project and a member on their own queue', async () => {
    // A default about attention, not permission — either can switch.
    expect((await shared('PM')).scope).toBe('ALL');
    expect((await shared('MEMBER')).scope).toBe('MINE');
  });

  it('MINE shows only the caller\'s tasks', async () => {
    const s = await shared('MEMBER');
    s.createTask('Mine', 'MEDIUM', 'TODO', { assignees: [{ id: 1, full_name: 'Ada' }] });
    s.createTask('Someone else\'s', 'MEDIUM', 'TODO', { assignees: [{ id: 2, full_name: 'Bob' }] });

    expect(s.filteredTasks.map((t) => t.title)).toEqual(['Mine']);

    s.setScope('ALL');
    expect(s.filteredTasks).toHaveLength(2);
  });

  it('filters to one named person', async () => {
    // The member view needs this: seeing what a teammate is carrying is how you
    // know who to ask, and it is not a permission question.
    const s = await shared('MEMBER');
    s.createTask('Mine', 'MEDIUM', 'TODO', { assignees: [{ id: 1, full_name: 'Ada' }] });
    s.createTask('Bob\'s', 'MEDIUM', 'TODO', { assignees: [{ id: 2, full_name: 'Bob' }] });

    s.setScope(2);
    expect(s.filteredTasks.map((t) => t.title)).toEqual(['Bob\'s']);
  });

  it('shows a shared task under every one of its assignees', async () => {
    const s = await shared('PM');
    s.createTask('Pair work', 'MEDIUM', 'TODO', {
      assignees: [{ id: 1, full_name: 'Ada' }, { id: 2, full_name: 'Bob' }],
    });

    s.setScope('MINE');
    expect(s.filteredTasks).toHaveLength(1);
    s.setScope(2);
    expect(s.filteredTasks).toHaveLength(1);
  });

  it('MINE hides unassigned work rather than claiming it', async () => {
    const s = await shared('MEMBER');
    s.createTask('Nobody owns this');
    expect(s.filteredTasks).toHaveLength(0);
  });
});

describe('invitations', () => {
  it('loads pending invitations after authenticating', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([]);
    apiMock.listInvitations.mockResolvedValue([invitation()]);

    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);

    expect(s.invitations).toHaveLength(1);
    expect(s.invitations[0]!.project_name).toBe('Orion');
  });

  it('still loads the board when invitations fail', async () => {
    // An invitation is a nicety; the board is the product.
    const s = store();
    apiMock.listProjects.mockResolvedValue([project()]);
    apiMock.listInvitations.mockRejectedValue(new Error('boom'));

    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);

    expect(s.appView).toBe('BOARD');
    expect(s.invitations).toEqual([]);
  });

  it('accepting opens the project and clears the invitation', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([]);
    apiMock.listInvitations.mockResolvedValue([invitation({ project_id: 7 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);

    apiMock.acceptInvitation.mockResolvedValue(project({ id: 7, my_role: 'MEMBER' }));
    apiMock.listProjects.mockResolvedValue([project({ id: 7, my_role: 'MEMBER' })]);
    await s.acceptInvitation(7);

    expect(s.invitations).toEqual([]);
    expect(s.currentProjectId).toBe(7);
    expect(s.isDashboardOpen).toBe(false);
  });

  it('declining removes it without joining anything', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([]);
    apiMock.listInvitations.mockResolvedValue([invitation({ project_id: 7 })]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);

    await s.declineInvitation(7);

    expect(apiMock.declineInvitation).toHaveBeenCalledWith(7);
    expect(s.invitations).toEqual([]);
    expect(s.currentProjectId).toBeNull();
  });

  it('clears invitations on sign-out', async () => {
    const s = store();
    apiMock.listProjects.mockResolvedValue([]);
    apiMock.listInvitations.mockResolvedValue([invitation()]);
    await s.onAuthenticated({ id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any);

    await s.logout();

    expect(s.invitations).toEqual([]);
  });
});
