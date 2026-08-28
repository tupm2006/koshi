// @vitest-environment jsdom
/**
 * Tests for the authentication dialog (D5 GAP-10).
 *
 * This component handles credentials, so it is the highest-value component to
 * cover: it must send exactly what the user typed, never leak the password, and
 * surface a failure rather than appearing to succeed.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    login: vi.fn(),
    register: vi.fn(),
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    listProjects: vi.fn(async () => []),
    getTasks: vi.fn(async () => []),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import AuthDialog from './AuthDialog.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeUser } from './testing';

function open(mode: 'LOGIN' | 'REGISTER' = 'LOGIN') {
  return mountWithPinia(AuthDialog, { props: { mode } });
}

const emailField = (w: any) => w.find('#auth-email');
const passwordField = (w: any) => w.find('#auth-password');

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.listProjects.mockResolvedValue([]);
  apiMock.login.mockResolvedValue({ access_token: 't', token_type: 'bearer', user: fakeUser() });
  apiMock.register.mockResolvedValue({ access_token: 't', token_type: 'bearer', user: fakeUser() });
});

describe('rendering', () => {
  it('opens in the requested mode', () => {
    expect(open('LOGIN').text()).toContain('Sign in');
    expect(open('REGISTER').text()).toContain('Create your account');
  });

  it('starts with empty credentials', () => {
    // A previous version pre-filled the seeded demo account, so a user who had
    // just registered saw somebody else's email (F-19 / DEC-012).
    const w = open('LOGIN');
    expect((emailField(w).element as HTMLInputElement).value).toBe('');
    expect((passwordField(w).element as HTMLInputElement).value).toBe('');
  });

  it('masks the password field', () => {
    expect(passwordField(open()).attributes('type')).toBe('password');
  });

  it('asks for name and skills only when registering', () => {
    expect(open('LOGIN').find('#auth-name').exists()).toBe(false);
    expect(open('REGISTER').find('#auth-name').exists()).toBe(true);
    expect(open('REGISTER').find('#auth-skills').exists()).toBe(true);
  });

  it('offers no role selector when registering', () => {
    // Roles are per-project; registration must not let a client pick one.
    const w = open('REGISTER');
    expect(w.find('select').exists()).toBe(false);
    expect(w.text().toLowerCase()).not.toContain('project manager (pm)');
  });

  it('switches between sign-in and sign-up', async () => {
    const w = open('LOGIN');
    await w.findAll('button').find((b) => b.text().includes("Don't have an account"))!.trigger('click');
    expect(w.find('#auth-name').exists()).toBe(true);
  });
});

describe('submission', () => {
  it('signs in with exactly what was typed', async () => {
    // NOTE: `.trim()` on the email cannot be observed here — an <input
    // type="email"> already applies the HTML value-sanitisation algorithm, so
    // jsdom strips surrounding whitespace before the component ever sees it.
    // The trim in the component is belt-and-braces for programmatic values.
    const w = open('LOGIN');
    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('hunter2');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.login).toHaveBeenCalledWith('ada@example.com', 'hunter2');
    expect(apiMock.register).not.toHaveBeenCalled();
  });

  it('registers with name and skills, and sends no role', async () => {
    const w = open('REGISTER');
    await w.find('#auth-name').setValue('Ada Lovelace');
    await w.find('#auth-skills').setValue('python');
    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('hunter2');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.register).toHaveBeenCalledWith('ada@example.com', 'hunter2', 'Ada Lovelace', 'python');
    // Four positional arguments only — no role smuggled in as a fifth.
    expect(apiMock.register.mock.calls[0]).toHaveLength(4);
  });

  it('omits blank skills rather than sending an empty string', async () => {
    const w = open('REGISTER');
    await w.find('#auth-name').setValue('Ada');
    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('hunter2');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.register.mock.calls[0]![3]).toBeUndefined();
  });

  it('runs the shared post-auth path so the board is actually loaded', async () => {
    // DEC-012: login used to skip loadProjects, leaving a signed-in user on an
    // empty board with no route forward.
    const w = open('LOGIN');
    const store = useTaskStore();
    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('hunter2');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(apiMock.listProjects).toHaveBeenCalled();
    expect(store.currentUser).toMatchObject({ email: 'ada@example.com' });
    expect(store.appView).toBe('BOARD');
  });

  it('clears the password once the request succeeds', async () => {
    const w = open('LOGIN');
    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('hunter2');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect((passwordField(w).element as HTMLInputElement).value).toBe('');
  });
});

describe('failure handling', () => {
  it('shows the server message and does not sign the user in', async () => {
    apiMock.login.mockRejectedValue(new Error('Invalid email or password'));
    const w = open('LOGIN');
    const store = useTaskStore();

    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('wrong');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect(w.text()).toContain('Invalid email or password');
    expect(store.currentUser).toBeNull();
    expect(store.appView).not.toBe('BOARD');
  });

  it('keeps the password on screen after a failure so it can be corrected', async () => {
    apiMock.login.mockRejectedValue(new Error('nope'));
    const w = open('LOGIN');
    await emailField(w).setValue('ada@example.com');
    await passwordField(w).setValue('typo');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();

    expect((passwordField(w).element as HTMLInputElement).value).toBe('typo');
  });

  it('clears a previous error when switching mode', async () => {
    apiMock.login.mockRejectedValue(new Error('Invalid email or password'));
    const w = open('LOGIN');
    await emailField(w).setValue('a@b.c');
    await passwordField(w).setValue('x');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(w.text()).toContain('Invalid email or password');

    await w.findAll('button').find((b) => b.text().includes("Don't have an account"))!.trigger('click');
    expect(w.text()).not.toContain('Invalid email or password');
  });
});

describe('dismissal', () => {
  it('emits close from the close button', async () => {
    const w = open();
    await w.find('[aria-label]').trigger('click');
    expect(w.emitted('close')).toBeTruthy();
  });

  it('emits close when the backdrop is clicked', async () => {
    const w = open();
    await w.find('[role="dialog"]').trigger('click');
    expect(w.emitted('close')).toBeTruthy();
  });
});
