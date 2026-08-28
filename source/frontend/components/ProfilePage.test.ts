// @vitest-environment jsdom
/**
 * Tests for the profile page (D5 GAP-10).
 *
 * It edits account data and owns the only sign-out control, so the assertions
 * focus on: showing the signed-in user rather than a stale one, sending only
 * what changed, and clearing the session on sign-out.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    updateProfile: vi.fn(),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import ProfilePage from './ProfilePage.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeUser, fakeProject } from './testing';

async function open(over: { user?: any; projects?: any[] } = {}) {
  const user = over.user ?? fakeUser();
  const projects = over.projects ?? [fakeProject()];

  // onMounted calls loadProjects(), so the API has to agree with the state we
  // seed or the component would immediately overwrite it.
  apiMock.listProjects.mockResolvedValue(projects);

  const w = mountWithPinia(ProfilePage, {
    setup: () => {
      const s = useTaskStore();
      s.currentUser = user as any;
      s.projects = projects as any;
      s.currentProjectId = projects[0]?.id ?? null;
      s.appView = 'PROFILE';
    },
  });

  await flushPromises();
  await w.vm.$nextTick();
  return { w, store: useTaskStore() };
}

const nameField = (w: any) => w.find('#profile-name');
const skillsField = (w: any) => w.find('#profile-skills');
const buttonWith = (w: any, text: string) =>
  w.findAll('button').find((b: any) => b.text().includes(text));

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.listProjects.mockResolvedValue([fakeProject()]);
  apiMock.updateProfile.mockImplementation(async (_id: number, changes: any) => fakeUser(changes));
});

describe('identity', () => {
  it('shows the signed-in account, not a hardcoded one', async () => {
    const { w } = await open({ user: fakeUser({ full_name: 'Grace Hopper', email: 'grace@navy.mil' }) });
    expect(w.text()).toContain('Grace Hopper');
    expect(w.text()).toContain('grace@navy.mil');
  });

  it('falls back to initials when there is no avatar', async () => {
    const { w } = await open({ user: fakeUser({ full_name: 'Grace Hopper', avatar_url: null }) });
    expect(w.find('img').exists()).toBe(false);
    expect(w.text()).toContain('GH');
  });

  it('renders an avatar when one is present', async () => {
    const { w } = await open({ user: fakeUser({ avatar_url: 'https://example.com/a.png' }) });
    expect(w.find('img').attributes('src')).toBe('https://example.com/a.png');
  });

  it('counts projects and the ones the user manages', async () => {
    const { w } = await open({
      projects: [
        fakeProject({ id: 1, my_role: 'PM' }),
        fakeProject({ id: 2, my_role: 'MEMBER' }),
        fakeProject({ id: 3, my_role: 'PM' }),
      ],
    });
    const stats = w.findAll('dd').map((d) => d.text());
    expect(stats[0]).toBe('3'); // projects
    expect(stats[1]).toBe('2'); // managing
  });
});

describe('editing', () => {
  it('prefills the form from the current user', async () => {
    const { w } = await open({ user: fakeUser({ full_name: 'Ada Lovelace', skills: 'python,vue' }) });
    expect((nameField(w).element as HTMLInputElement).value).toBe('Ada Lovelace');
    expect((skillsField(w).element as HTMLInputElement).value).toBe('python,vue');
  });

  it('disables save until something actually changes', async () => {
    const { w } = await open();
    expect(buttonWith(w, 'Save changes')!.attributes('disabled')).toBeDefined();

    await nameField(w).setValue('Ada L.');
    expect(buttonWith(w, 'Save changes')!.attributes('disabled')).toBeUndefined();
  });

  it('sends nothing when the form is submitted unchanged', async () => {
    // The disabled button is the visible guard; this covers the handler itself,
    // which a form can still reach via Enter.
    const { w } = await open();
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.updateProfile).not.toHaveBeenCalled();
  });

  it('sends the edited fields and updates the store', async () => {
    const { w, store } = await open();
    await nameField(w).setValue('Ada L.');
    await skillsField(w).setValue('rust');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.updateProfile).toHaveBeenCalledWith(1, { full_name: 'Ada L.', skills: 'rust' });
    expect(store.currentUser).toMatchObject({ full_name: 'Ada L.', skills: 'rust' });
    expect(w.text()).toContain('Profile saved.');
  });

  it('offers no way to edit the email', async () => {
    // Email identifies the account; the server refuses to change it here.
    const { w } = await open();
    const email = w.findAll('input[type="email"]')[0]!;
    expect(email.attributes('disabled')).toBeDefined();
  });

  it('offers no way to change a role', async () => {
    // Roles live on ProjectMember and are PM-gated per project.
    const { w } = await open();
    expect(w.find('select').exists()).toBe(false);
  });

  it('restores the original values on discard', async () => {
    const { w } = await open({ user: fakeUser({ full_name: 'Ada Lovelace' }) });
    await nameField(w).setValue('Typo');
    await buttonWith(w, 'Discard')!.trigger('click');
    expect((nameField(w).element as HTMLInputElement).value).toBe('Ada Lovelace');
  });

  it('surfaces a save failure instead of claiming success', async () => {
    apiMock.updateProfile.mockRejectedValue(new Error('Server unavailable'));
    const { w } = await open();
    await nameField(w).setValue('Ada L.');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(w.text()).toContain('Server unavailable');
    expect(w.text()).not.toContain('Profile saved.');
  });
});

describe('memberships', () => {
  it('lists each project with the role held in it', async () => {
    const { w } = await open({
      projects: [
        fakeProject({ id: 1, name: 'Apollo', my_role: 'PM' }),
        fakeProject({ id: 2, name: 'Zephyr', my_role: 'MEMBER' }),
      ],
    });
    const text = w.text();
    expect(text).toContain('Apollo');
    expect(text).toContain('Zephyr');
    expect(text).toContain('PM');
    expect(text).toContain('MEMBER');
  });

  it('says so when the account belongs to nothing', async () => {
    const { w } = await open({ projects: [] });
    expect(w.text()).toContain('not a member of any project');
  });

  it('selecting a project opens its board', async () => {
    const { w, store } = await open({
      projects: [fakeProject({ id: 1, name: 'Apollo' }), fakeProject({ id: 2, name: 'Zephyr' })],
    });
    await buttonWith(w, 'Zephyr')!.trigger('click');
    await flushPromises();

    expect(store.currentProjectId).toBe(2);
    expect(store.appView).toBe('BOARD');
  });
});

describe('session', () => {
  it('signs out, clearing the session and returning to the landing page', async () => {
    const { w, store } = await open();
    await buttonWith(w, 'Sign out')!.trigger('click');
    await flushPromises();

    expect(apiMock.logout).toHaveBeenCalled();
    expect(store.currentUser).toBeNull();
    expect(store.projects).toEqual([]);
    expect(store.appView).toBe('LANDING');
  });

  it('returns to the board without signing out', async () => {
    const { w, store } = await open();
    await buttonWith(w, 'Back to board')!.trigger('click');

    expect(store.appView).toBe('BOARD');
    expect(store.currentUser).not.toBeNull();
  });
});
