// @vitest-environment jsdom
/**
 * SprintPanel (DEC-028). The server owns the Scrum rules and is tested there
 * (tests/test_scrum.py); these cover what only the client does: which calls
 * are made, who is offered the controls, and that planning re-syncs the board.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    fetchBlob: vi.fn(async () => new Blob()),
    listProjects: vi.fn(async () => [] as any[]),
    listMembers: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    listSprints: vi.fn(async () => [] as any[]),
    getVelocity: vi.fn(async () => [] as any[]),
    getBurndown: vi.fn(async (): Promise<any> => ({ sprint_id: 1, total_points: 0, days: [] })),
    createSprint: vi.fn(),
    startSprint: vi.fn(),
    completeSprint: vi.fn(),
    deleteSprint: vi.fn(),
    setTaskSprint: vi.fn(),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import SprintPanel from './SprintPanel.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeProject, stubIcons } from './testing';

const sprint = (over: any = {}) => ({
  id: 1, project_id: 1, name: 'Sprint 1', goal: 'g', start_date: '2026-10-20T00:00:00',
  end_date: '2026-10-30T00:00:00', is_active: false, state: 'PLANNED', completed_at: null,
  committed_points: null, ...over,
});
const task = (over: any = {}) => ({ id: 10, key: 'TSK-10', title: 'Login', status: 'TODO', complexity_points: 3, sprint_id: null, ...over });

let store: ReturnType<typeof useTaskStore>;
async function open(role: 'PM' | 'MEMBER' = 'PM', connected = true) {
  const w = mountWithPinia(SprintPanel, {
    global: { stubs: stubIcons(['Play', 'CheckCircle2', 'Plus', 'Timer']) },
    setup: () => {
      store = useTaskStore();
      store.currentUser = { id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any;
      store.projects = [fakeProject({ my_role: role, member_count: 2 })] as any;
      store.currentProjectId = 1;
      store.isBackendConnected = connected;
    },
  });
  await flushPromises();
  return w;
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.listSprints.mockResolvedValue([sprint()]);
  apiMock.getTasks.mockResolvedValue([task(), task({ id: 11, key: 'TSK-11', sprint_id: 1, complexity_points: 5 })]);
});

describe('SprintPanel', () => {
  it('loads sprints, tasks and velocity for the current project', async () => {
    const w = await open();
    expect(apiMock.listSprints).toHaveBeenCalledWith(1);
    expect(apiMock.getVelocity).toHaveBeenCalledWith(1);
    expect(w.find('[data-sprint="1"]').text()).toContain('Sprint 1');
    expect(w.find('[data-sprint="1"]').text()).toContain('5');
  });

  it('a PM can start a planned sprint', async () => {
    apiMock.startSprint.mockResolvedValue(sprint({ state: 'ACTIVE' }));
    const w = await open();
    await w.find('[data-action="start"]').trigger('click');
    await flushPromises();
    expect(apiMock.startSprint).toHaveBeenCalledWith(1);
  });

  it('a member is shown no lifecycle controls or create form', async () => {
    const w = await open('MEMBER');
    expect(w.find('[data-action="start"]').exists()).toBe(false);
    expect(w.find('[data-testid="sprint-form"]').exists()).toBe(false);
  });

  it('a PM offline in a shared project gets no controls (canMutate)', async () => {
    const w = await open('PM', false);
    expect(w.find('[data-action="start"]').exists()).toBe(false);
  });

  it('completing passes the chosen destination for unfinished work', async () => {
    apiMock.listSprints.mockResolvedValue([sprint({ state: 'ACTIVE', is_active: true }), sprint({ id: 2, name: 'Sprint 2' })]);
    apiMock.completeSprint.mockResolvedValue(sprint({ state: 'COMPLETED' }));
    const w = await open();
    await w.find('select').setValue('2');
    await w.find('[data-action="complete"]').trigger('click');
    await flushPromises();
    expect(apiMock.completeSprint).toHaveBeenCalledWith(1, 2);
  });

  it('planning a backlog item moves it into the selected sprint and re-syncs the board', async () => {
    apiMock.setTaskSprint.mockResolvedValue({});
    const sync = vi.fn(async () => {});
    const w = await open();
    store.syncWithBackend = sync as any;
    await w.find('[data-tab="PLANNING"]').trigger('click');
    expect(w.findAll('[data-backlog-task]')).toHaveLength(1);
    expect(w.findAll('[data-sprint-task]')).toHaveLength(1);
    await w.find('[data-backlog-task] button').trigger('click');
    await flushPromises();
    expect(apiMock.setTaskSprint).toHaveBeenCalledWith(10, 1);
    expect(sync).toHaveBeenCalledWith(1);
  });

  it('shows the server error instead of failing silently', async () => {
    apiMock.startSprint.mockRejectedValue(new Error("Sprint 'X' is already active; complete it first"));
    const w = await open();
    await w.find('[data-action="start"]').trigger('click');
    await flushPromises();
    expect(w.find('[data-testid="scrum-error"]').text()).toContain('already active');
  });

  it('draws a burndown with remaining points for elapsed days only', async () => {
    apiMock.getBurndown.mockResolvedValue({ sprint_id: 1, total_points: 8, days: [
      { date: '2026-10-20', ideal: 8, remaining: 8 },
      { date: '2026-10-21', ideal: 4, remaining: 5 },
      { date: '2026-10-22', ideal: 0, remaining: null },
    ] });
    const w = await open();
    await w.find('[data-tab="BURNDOWN"]').trigger('click');
    await flushPromises();
    expect(w.find('[data-testid="burndown"]').exists()).toBe(true);
    expect(w.findAll('[data-testid="burndown"] circle')).toHaveLength(2);
  });

  it('averages velocity over completed sprints', async () => {
    apiMock.getVelocity.mockResolvedValue([
      { sprint_id: 1, sprint_name: 'S1', committed_points: 10, completed_points: 8 },
      { sprint_id: 2, sprint_name: 'S2', committed_points: 12, completed_points: 11 },
    ]);
    const w = await open();
    await w.find('[data-tab="VELOCITY"]').trigger('click');
    expect(w.find('[data-testid="velocity-avg"]').text()).toBe('9.5');
  });
});
