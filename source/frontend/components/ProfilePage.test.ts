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
    uploadAvatar: vi.fn(),
    removeAvatar: vi.fn(),
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

describe('profile picture', () => {
  const pick = async (w: any, file: File) => {
    const input = w.find('#avatar-upload input[type="file"]').element as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [file], configurable: true });
    await w.find('#avatar-upload input[type="file"]').trigger('change');
    await flushPromises();
  };

  it('offers an upload control on the picture itself', async () => {
    // One thing, one place: a separate upload button elsewhere would make you
    // look in two places for the same action.
    const { w } = await open();
    expect(w.find('#avatar-upload').exists()).toBe(true);
  });

  it('uploads the chosen image and shows it', async () => {
    apiMock.uploadAvatar.mockResolvedValue(fakeUser({ avatar_url: '/api/users/1/avatar?v=abc' }));
    const { w } = await open();

    await pick(w, new File(['x'], 'face.png', { type: 'image/png' }));

    expect(apiMock.uploadAvatar).toHaveBeenCalled();
    expect(w.find('img').attributes('src')).toBe('/api/users/1/avatar?v=abc');
  });

  it('refuses an oversized file without calling the server', async () => {
    // A courtesy, not a substitute for the server check — it fails instantly
    // rather than after uploading two megabytes.
    const { w } = await open();
    const big = new File([new Uint8Array(3 * 1024 * 1024)], 'huge.png', { type: 'image/png' });

    await pick(w, big);

    expect(apiMock.uploadAvatar).not.toHaveBeenCalled();
    expect(w.find('#avatar-error').text()).toMatch(/2 MB/);
  });

  it('surfaces a server rejection', async () => {
    apiMock.uploadAvatar.mockRejectedValue(new Error('Unsupported file type'));
    const { w } = await open();

    await pick(w, new File(['x'], 'clip.mp4', { type: 'video/mp4' }));

    expect(w.find('#avatar-error').text()).toContain('Unsupported file type');
  });

  it('offers removal only when there is a picture to remove', async () => {
    const { w } = await open();
    expect(w.find('#avatar-remove').exists()).toBe(false);

    apiMock.uploadAvatar.mockResolvedValue(fakeUser({ avatar_url: '/api/users/1/avatar?v=abc' }));
    await pick(w, new File(['x'], 'face.png', { type: 'image/png' }));

    expect(w.find('#avatar-remove').exists()).toBe(true);
  });

  it('removing falls back to initials', async () => {
    apiMock.uploadAvatar.mockResolvedValue(fakeUser({ avatar_url: '/api/users/1/avatar?v=abc' }));
    apiMock.removeAvatar.mockResolvedValue(fakeUser({ avatar_url: null }));
    const { w } = await open();
    await pick(w, new File(['x'], 'face.png', { type: 'image/png' }));

    await w.find('#avatar-remove').trigger('click');
    await flushPromises();

    expect(w.find('img').exists()).toBe(false);
    expect(w.text()).toContain('AL');  // Ada Lovelace
  });
});

describe('pasting a profile picture', () => {
  const paste = (w: any, files: File[], target?: any) => {
    const ev: any = new Event('paste', { bubbles: true, cancelable: true });
    ev.clipboardData = { items: files.map((f) => ({ kind: 'file', getAsFile: () => f })) };
    (target ?? w.element).dispatchEvent(ev);
    return ev;
  };

  it('uploads an image pasted anywhere on the page', async () => {
    // There is no field to focus first — you copy an image and press Ctrl+V.
    apiMock.uploadAvatar.mockResolvedValue(fakeUser({ avatar_url: '/api/users/1/avatar?v=abc' }));
    const { w } = await open();

    paste(w, [new File(['x'], 'me.png', { type: 'image/png' })]);
    await flushPromises();

    expect(apiMock.uploadAvatar).toHaveBeenCalled();
  });

  it('ignores a paste into the name field, where it means text', async () => {
    const { w } = await open();

    paste(w, [new File(['x'], 'me.png', { type: 'image/png' })],
      w.find('#profile-name').element);
    await flushPromises();

    expect(apiMock.uploadAvatar).not.toHaveBeenCalled();
  });

  it('ignores a pasted non-image', async () => {
    const { w } = await open();

    paste(w, [new File(['x'], 'notes.pdf', { type: 'application/pdf' })]);
    await flushPromises();

    expect(apiMock.uploadAvatar).not.toHaveBeenCalled();
  });

  it('applies the same size limit as the file picker', async () => {
    const { w } = await open();

    paste(w, [new File([new Uint8Array(3 * 1024 * 1024)], 'huge.png', { type: 'image/png' })]);
    await flushPromises();

    expect(apiMock.uploadAvatar).not.toHaveBeenCalled();
    expect(w.find('#avatar-error').text()).toMatch(/2 MB/);
  });
});
