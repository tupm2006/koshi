// @vitest-environment jsdom
/**
 * Tests for the project dashboard (D5 GAP-10).
 *
 * The dashboard hides role controls from non-PMs. That is an affordance, not a
 * security boundary — the server refuses the same actions independently
 * (D6 P11, asserted in `test_projects_and_roles.py`). These tests cover the
 * affordance; they are not a substitute for the server-side checks.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    createProject: vi.fn(),
    listMembers: vi.fn(async () => [] as any[]),
    addMember: vi.fn(),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn(),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import ProjectDashboard from './ProjectDashboard.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeUser, fakeProject } from './testing';

const member = (over: Record<string, unknown> = {}) => ({
  user_id: 2, project_id: 1, role: 'MEMBER',
  full_name: 'Grace Hopper', email: 'grace@navy.mil', skills: 'cobol',
  avatar_url: null, active_tasks_count: 3, wip_points: 7, ...over,
});

async function open(over: { projects?: any[]; members?: any[] } = {}) {
  const projects = over.projects ?? [fakeProject({ my_role: 'PM' })];
  apiMock.listProjects.mockResolvedValue(projects);
  apiMock.listMembers.mockResolvedValue(over.members ?? [member()]);

  const w = mountWithPinia(ProjectDashboard, {
    setup: () => {
      const s = useTaskStore();
      s.currentUser = fakeUser() as any;
      s.projects = projects as any;
      s.currentProjectId = projects[0]?.id ?? null;
    },
  });
  await flushPromises();
  await w.vm.$nextTick();
  return { w, store: useTaskStore() };
}

const buttonWith = (w: any, text: string) =>
  w.findAll('button').find((b: any) => b.text().includes(text));

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.createProject.mockImplementation(async (name: string) =>
    fakeProject({ id: 99, name, my_role: 'PM', member_count: 1 }));
  apiMock.addMember.mockResolvedValue(member());
  apiMock.updateMemberRole.mockResolvedValue(member({ role: 'PM' }));
  apiMock.removeMember.mockResolvedValue(undefined);
});

describe('projects', () => {
  it('lists the caller projects with the role held in each', async () => {
    const { w } = await open({
      projects: [
        fakeProject({ id: 1, name: 'Apollo', my_role: 'PM' }),
        fakeProject({ id: 2, name: 'Zephyr', my_role: 'MEMBER' }),
      ],
    });
    expect(w.text()).toContain('Apollo');
    expect(w.text()).toContain('Zephyr');
    expect(w.text()).toContain('Projects (2)');
  });

  it('prompts when the account has no projects', async () => {
    const { w } = await open({ projects: [] });
    expect(w.text()).toContain('no projects yet');
  });

  it('creates a project and selects it', async () => {
    const { w, store } = await open({ projects: [] });
    await w.find('#new-project-name').setValue('Orion');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.createProject).toHaveBeenCalledWith('Orion', '');
    expect(store.currentProjectId).toBe(99);
    expect(w.text()).toContain('you are its PM');
  });
});

describe('PM affordances', () => {
  it('lets a PM change a member role', async () => {
    const { w } = await open();
    const select = w.find('select');
    expect(select.exists()).toBe(true);

    await select.setValue('PM');
    await flushPromises();
    expect(apiMock.updateMemberRole).toHaveBeenCalledWith(1, 2, 'PM');
  });

  it('lets a PM add a member by email', async () => {
    const { w } = await open();
    await w.find('#invite-email').setValue('new@example.com');
    await w.findAll('form')[1]!.trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.addMember).toHaveBeenCalledWith(1, 'new@example.com', 'MEMBER');
  });

  it('lets a PM remove a member', async () => {
    const { w } = await open();
    await w.find('[title="Remove from project"]').trigger('click');
    await flushPromises();
    expect(apiMock.removeMember).toHaveBeenCalledWith(1, 2);
  });

  it('shows each member workload alongside their role', async () => {
    const { w } = await open({ members: [member({ active_tasks_count: 4, wip_points: 9 })] });
    expect(w.text()).toContain('4 active');
    expect(w.text()).toContain('9 pts');
  });
});

describe('MEMBER restrictions', () => {
  async function asMember() {
    return open({ projects: [fakeProject({ id: 1, my_role: 'MEMBER', member_count: 2 })] });
  }

  it('hides the role selector', async () => {
    const { w } = await asMember();
    expect(w.find('select').exists()).toBe(false);
  });

  it('hides the remove control', async () => {
    const { w } = await asMember();
    expect(w.find('[title="Remove from project"]').exists()).toBe(false);
  });

  it('hides the add-member form', async () => {
    const { w } = await asMember();
    expect(w.find('#invite-email').exists()).toBe(false);
  });

  it('explains why the controls are absent', async () => {
    const { w } = await asMember();
    expect(w.text()).toContain('Only a PM can change roles');
  });

  it('still shows the roster read-only', async () => {
    const { w } = await asMember();
    expect(w.text()).toContain('Grace Hopper');
    expect(w.text()).toContain('MEMBER');
  });
});

describe('failure handling', () => {
  it('surfaces a rejected role change rather than appearing to succeed', async () => {
    // The server is the real boundary; if it refuses, say so.
    apiMock.updateMemberRole.mockRejectedValue(new Error('Access forbidden'));
    const { w } = await open();

    await w.find('select').setValue('PM');
    await flushPromises();

    expect(w.text()).toContain('Access forbidden');
  });

  it('surfaces a rejected invite', async () => {
    apiMock.addMember.mockRejectedValue(new Error('User not found'));
    const { w } = await open();

    await w.find('#invite-email').setValue('ghost@example.com');
    await w.findAll('form')[1]!.trigger('submit.prevent');
    await flushPromises();

    expect(w.text()).toContain('User not found');
  });
});
