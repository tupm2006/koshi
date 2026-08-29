// @vitest-environment jsdom
/**
 * Avatars, the comment thread, and the completion-evidence prompt.
 *
 * The thread is where a mistake would be most expensive: it posts to the
 * server, uploads files, and renders other people's content back into the page.
 * So the tests here care about what is sent, what happens when part of it
 * fails, and what is rendered for a type that is not an image.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    listMembers: vi.fn(async () => [] as any[]),
    listInvitations: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    createTask: vi.fn(async () => ({})),
    updateTask: vi.fn(async () => ({})),
    deleteTask: vi.fn(async () => undefined),
    listComments: vi.fn(async () => [] as any[]),
    addComment: vi.fn(),
    uploadAttachment: vi.fn(),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import AssigneeAvatars from './AssigneeAvatars.vue';
import CommentThread from './CommentThread.vue';
import EvidenceModal from './EvidenceModal.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeProject } from './testing';

type Store = ReturnType<typeof useTaskStore>;

const person = (id: number, full_name: string, avatar_url: string | null = null) =>
  ({ id, full_name, avatar_url });

const comment = (over: Record<string, unknown> = {}) => ({
  id: 1,
  task_id: 10,
  author_id: 1,
  author: { id: 1, full_name: 'Ada Lovelace', email: 'a@b.c', skills: '' },
  content: 'Looks fine to me',
  kind: 'COMMENT',
  // Mirrors the server, which always sends these. Without parent_id the
  // threading filter treats every comment as a reply to nothing and drops it.
  parent_id: null,
  mentions: [],
  attachments: [],
  created_at: '2026-08-28T10:00:00Z',
  ...over,
});

const roster = (over: Record<string, unknown> = {}) => ({
  user_id: 2, project_id: 1, role: 'MEMBER', status: 'ACCEPTED',
  full_name: 'Grace Hopper', email: 'grace@navy.mil', skills: '',
  avatar_url: null, active_tasks_count: 0, wip_points: 0, ...over,
});

/** A clipboard event carrying files, as jsdom does not construct one. */
function pasteEvent(files: File[]): any {
  const ev: any = new Event('paste', { bubbles: true, cancelable: true });
  ev.clipboardData = {
    items: files.map((f) => ({ kind: 'file', getAsFile: () => f })),
  };
  return ev;
}

const attachment = (over: Record<string, unknown> = {}) => ({
  id: 5, filename: 'shot.png', content_type: 'image/png',
  size_bytes: 2048, url: '/api/tasks/attachments/5', ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.listComments.mockResolvedValue([]);
  apiMock.addComment.mockResolvedValue(comment({ id: 99 }));
  apiMock.uploadAttachment.mockResolvedValue(attachment());
});

// ---------------------------------------------------------------------------
// AssigneeAvatars
// ---------------------------------------------------------------------------

describe('AssigneeAvatars', () => {
  const mount = (assignees: any[], props: any = {}) =>
    mountWithPinia(AssigneeAvatars, { props: { assignees, ...props } });

  it('renders nothing when nobody is assigned', () => {
    // An empty circle would say "assigned" when the task is not.
    expect(mount([]).find('[data-assignees]').exists()).toBe(false);
  });

  it('shows initials from the first and last name', () => {
    // "Phạm Minh Tú" reads as PT, not PM.
    expect(mount([person(1, 'Phạm Minh Tú')]).text()).toBe('PT');
  });

  it('handles a single-word name', () => {
    expect(mount([person(1, 'Ada')]).text()).toBe('A');
  });

  it('collapses the overflow into a count', () => {
    const w = mount([1, 2, 3, 4, 5].map((i) => person(i, `User ${i}`)), { max: 3 });
    expect(w.findAll('[data-assignee]')).toHaveLength(3);
    expect(w.text()).toContain('+2');
  });

  it('names the hidden people in the overflow tooltip', () => {
    const w = mount([person(1, 'A A'), person(2, 'B B'), person(3, 'Grace Hopper')], { max: 2 });
    expect(w.html()).toContain('Grace Hopper');
  });

  it('gives the same person the same colour every time', () => {
    // Recognition at a glance is the whole point; a colour that moves when
    // somebody is renamed would defeat it, so it is derived from the id.
    const a = mount([person(7, 'Ada Lovelace')]).find('[data-assignee]').classes();
    const b = mount([person(7, 'Renamed Person')]).find('[data-assignee]').classes();
    expect(a.filter((c) => c.startsWith('bg-'))).toEqual(b.filter((c) => c.startsWith('bg-')));
  });

  it('prefers a real avatar over initials', () => {
    const w = mount([person(1, 'Ada Lovelace', 'https://example.test/a.png')]);
    expect(w.find('img').attributes('src')).toBe('https://example.test/a.png');
    expect(w.text()).not.toContain('AL');
  });

  it('titles each avatar with the full name for the non-obvious initials', () => {
    expect(mount([person(1, 'Ada Lovelace')]).find('[data-assignee]').attributes('title'))
      .toBe('Ada Lovelace');
  });
});

// ---------------------------------------------------------------------------
// CommentThread
// ---------------------------------------------------------------------------

describe('CommentThread', () => {
  function open(seed: (s: Store) => void = () => {}) {
    let store!: Store;
    const w = mountWithPinia(CommentThread, {
      props: { taskId: 'TSK-10' },
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

  it('loads the thread for its task', async () => {
    open();
    await flushPromises();
    // The display key is translated back to the server id.
    expect(apiMock.listComments).toHaveBeenCalledWith(10);
  });

  it('renders a comment with its author', async () => {
    apiMock.listComments.mockResolvedValue([comment()]);
    const { w } = open();
    await flushPromises();

    expect(w.text()).toContain('Looks fine to me');
    expect(w.text()).toContain('Ada Lovelace');
  });

  it('marks evidence distinctly from ordinary discussion', async () => {
    apiMock.listComments.mockResolvedValue([
      comment({ id: 1, kind: 'COMMENT' }),
      comment({ id: 2, kind: 'EVIDENCE', content: 'Deployed' }),
    ]);
    const { w } = open();
    await flushPromises();

    expect(w.find('[data-comment="2"]').attributes('data-kind')).toBe('EVIDENCE');
    expect(w.text()).toContain('evidence');
  });

  it('renders an image inline rather than as a download link', async () => {
    // Proof you have to download to look at is proof nobody looks at.
    apiMock.listComments.mockResolvedValue([comment({ attachments: [attachment()] })]);
    const { w } = open();
    await flushPromises();

    expect(w.find('[data-attachment="5"] img').attributes('src')).toBe('/api/tasks/attachments/5');
  });

  it('renders a video with controls', async () => {
    apiMock.listComments.mockResolvedValue([
      comment({ attachments: [attachment({ content_type: 'video/mp4', filename: 'clip.mp4' })] }),
    ]);
    const { w } = open();
    await flushPromises();

    const video = w.find('[data-attachment="5"] video');
    expect(video.exists()).toBe(true);
    expect(video.attributes('controls')).toBeDefined();
  });

  it('falls back to a link for anything it cannot display', async () => {
    apiMock.listComments.mockResolvedValue([
      comment({ attachments: [attachment({ content_type: 'application/pdf', filename: 'spec.pdf' })] }),
    ]);
    const { w } = open();
    await flushPromises();

    expect(w.find('[data-attachment="5"] a').attributes('href')).toBe('/api/tasks/attachments/5');
  });

  it('posts what was typed', async () => {
    const { w } = open();
    await flushPromises();

    await w.find('#comment-draft').setValue('Ready for review');
    await w.findAll('button').find((b: any) => /post/i.test(b.text()))!.trigger('click');
    await flushPromises();

    // Fourth argument is the reply target: null for a top-level comment.
    expect(apiMock.addComment).toHaveBeenCalledWith(10, 'Ready for review', 'COMMENT', null);
  });

  it('will not post an empty comment with no files', async () => {
    const { w } = open();
    await flushPromises();

    await w.find('#comment-draft').setValue('   ');
    const post = w.findAll('button').find((b: any) => /post/i.test(b.text()))!;
    expect(post.attributes('disabled')).toBeDefined();
  });

  it('clears the draft after a successful post', async () => {
    const { w } = open();
    await flushPromises();

    await w.find('#comment-draft').setValue('Done');
    await w.findAll('button').find((b: any) => /post/i.test(b.text()))!.trigger('click');
    await flushPromises();

    expect((w.find('#comment-draft').element as HTMLTextAreaElement).value).toBe('');
  });

  it('reports which file failed rather than claiming the whole post failed', async () => {
    // The comment landed. Saying "failed" would invite a duplicate.
    apiMock.uploadAttachment.mockRejectedValue(new Error('too large'));
    const { w } = open();
    await flushPromises();

    // Drive the real input rather than poking at internals: `pickFiles` is
    // part of the path under test.
    const input = w.find('input[type="file"]').element as HTMLInputElement;
    Object.defineProperty(input, 'files', {
      value: [new File(['x'], 'big.mp4', { type: 'video/mp4' })],
      configurable: true,
    });
    await w.find('input[type="file"]').trigger('change');
    await w.findAll('button').find((b: any) => /post/i.test(b.text()))!.trigger('click');
    await flushPromises();

    expect(apiMock.addComment).toHaveBeenCalled();
    expect(w.text()).toContain('big.mp4');
    expect(w.text()).toMatch(/did not upload/i);
  });

  it('surfaces a load failure', async () => {
    apiMock.listComments.mockRejectedValue(new Error('Server unavailable'));
    const { w } = open();
    await flushPromises();

    expect(w.text()).toContain('Server unavailable');
  });

  it('says discussion is unavailable offline instead of pretending to work', async () => {
    const { w } = open((s) => { s.isBackendConnected = false; });
    await flushPromises();

    expect(apiMock.listComments).not.toHaveBeenCalled();
    expect(w.text()).toMatch(/unavailable offline/i);
    expect(w.find('#comment-draft').exists()).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// EvidenceModal
// ---------------------------------------------------------------------------

describe('EvidenceModal', () => {
  function open() {
    let store!: Store;
    const w = mountWithPinia(EvidenceModal, {
      setup: () => {
        store = useTaskStore();
        store.currentUser = { id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any;
        store.projects = [fakeProject()] as any;
        store.currentProjectId = 1;
        store.isBackendConnected = true;
        const t = store.createTask('Ship the thing')!;
        // The modal only ever opens behind a completed task; setting the flag
        // without the transition would test a state the app cannot reach.
        store.setStatus(t.id, 'DONE');
      },
    });
    return { w, store };
  }

  it('names the task it is asking about', async () => {
    const { w } = open();
    await flushPromises();
    expect(w.text()).toContain('Ship the thing');
  });

  it('says plainly that evidence is optional', async () => {
    // The task is already DONE; this is a prompt, not a gate.
    const { w } = open();
    await flushPromises();
    expect(w.text()).toMatch(/optional/i);
  });

  it('skipping leaves the task done and posts nothing', async () => {
    const { w, store } = open();
    await flushPromises();
    const id = store.evidenceForTaskId!;

    await w.find('#evidence-skip').trigger('click');

    expect(store.evidenceForTaskId).toBeNull();
    expect(apiMock.addComment).not.toHaveBeenCalled();
    expect(store.tasks.find((t) => t.id === id)!.status).toBe('DONE');
  });

  it('saves the note as EVIDENCE, not as an ordinary comment', async () => {
    const { w, store } = open();
    await flushPromises();

    await w.find('#comment-draft').setValue('Deployed and verified');
    await w.find('#evidence-save').trigger('click');
    await flushPromises();

    expect(apiMock.addComment).toHaveBeenCalledWith(
      expect.any(Number), 'Deployed and verified', 'EVIDENCE', null,
    );
    expect(store.evidenceForTaskId).toBeNull();
  });

  it('renders nothing when no task is awaiting evidence', () => {
    const w = mountWithPinia(EvidenceModal, {
      setup: () => { useTaskStore().evidenceForTaskId = null; },
    });
    expect(w.find('#evidence-modal').exists()).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// The prompt is triggered from the store, on every path to DONE
// ---------------------------------------------------------------------------

describe('completing a task asks for evidence', () => {
  function board(seed: (s: Store) => void = () => {}) {
    let store!: Store;
    mountWithPinia(AssigneeAvatars, {
      props: { assignees: [] },
      setup: () => {
        store = useTaskStore();
        store.currentUser = { id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any;
        store.projects = [fakeProject()] as any;
        store.currentProjectId = 1;
        store.isBackendConnected = true;
        seed(store);
      },
    });
    return store;
  }

  it('asks when a task is set to DONE', () => {
    const s = board();
    const t = s.createTask('A task')!;
    s.setStatus(t.id, 'DONE');
    expect(s.evidenceForTaskId).toBe(t.id);
  });

  it('asks when the status cycle reaches DONE, not before', () => {
    const s = board();
    const t = s.createTask('A task')!;

    s.cycleStatus(t.id); // IN_PROGRESS
    s.cycleStatus(t.id); // BLOCKED
    expect(s.evidenceForTaskId).toBeNull();

    s.cycleStatus(t.id); // DONE
    expect(s.evidenceForTaskId).toBe(t.id);
  });

  it('does not ask again for a task that is already done', () => {
    const s = board();
    const t = s.createTask('A task')!;
    s.setStatus(t.id, 'DONE');
    s.dismissEvidencePrompt();

    s.updateTask(t.id, { status: 'DONE', title: 'Renamed' });
    expect(s.evidenceForTaskId).toBeNull();
  });

  it('does not ask offline, where there is nowhere to upload to', () => {
    const s = board((st) => { st.isBackendConnected = false; });
    const t = s.createTask('A task')!;
    s.setStatus(t.id, 'DONE');

    expect(s.evidenceForTaskId).toBeNull();
    // And the transition still happened — the prompt is not a gate.
    expect(s.tasks.find((x) => x.id === t.id)!.status).toBe('DONE');
  });
});

// ---------------------------------------------------------------------------
// Mentions and replies in the thread
// ---------------------------------------------------------------------------

describe('CommentThread — mentions', () => {
  function open(members: any[] = [roster()]) {
    let store!: Store;
    const w = mountWithPinia(CommentThread, {
      props: { taskId: 'TSK-10' },
      setup: () => {
        store = useTaskStore();
        store.currentUser = { id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any;
        store.projects = [fakeProject()] as any;
        store.currentProjectId = 1;
        store.isBackendConnected = true;
        store.members = members as any;
      },
    });
    return { w, store };
  }

  const type = async (w: any, text: string) => {
    const box = w.find('#comment-draft');
    (box.element as HTMLTextAreaElement).value = text;
    (box.element as HTMLTextAreaElement).setSelectionRange(text.length, text.length);
    await box.trigger('input');
    await box.trigger('keyup');
  };

  it('opens a picker when @ is typed', async () => {
    const { w } = open();
    await flushPromises();
    await type(w, 'hey @');

    expect(w.find('#mention-menu').exists()).toBe(true);
    expect(w.find('[data-mention-option="2"]').exists()).toBe(true);
  });

  it('filters the picker as you type', async () => {
    const { w } = open([roster({ user_id: 2, full_name: 'Grace Hopper' }),
                        roster({ user_id: 3, full_name: 'Alan Turing', email: 'alan@x.com' })]);
    await flushPromises();
    await type(w, '@gra');

    expect(w.find('[data-mention-option="2"]').exists()).toBe(true);
    expect(w.find('[data-mention-option="3"]').exists()).toBe(false);
  });

  it('does not open inside an email address', async () => {
    const { w } = open();
    await flushPromises();
    await type(w, 'write to ada@exam');

    expect(w.find('#mention-menu').exists()).toBe(false);
  });

  it('inserts a token carrying the id, not just the name', async () => {
    // The id is what the mention means — a rename must not break it.
    const { w } = open();
    await flushPromises();
    await type(w, 'hey @gra');
    await w.find('[data-mention-option="2"]').trigger('mousedown');
    await flushPromises();

    expect((w.find('#comment-draft').element as HTMLTextAreaElement).value)
      .toBe('hey @[Grace Hopper](2) ');
  });

  it('closes the picker after choosing', async () => {
    const { w } = open();
    await flushPromises();
    await type(w, '@g');
    await w.find('[data-mention-option="2"]').trigger('mousedown');
    await flushPromises();

    expect(w.find('#mention-menu').exists()).toBe(false);
  });

  it('renders a mention as a chip, with the current name', async () => {
    // The stored label says "Old Name"; the roster says otherwise, and the
    // roster is what the reader should see.
    apiMock.listComments.mockResolvedValue([comment({ content: 'ping @[Old Name](2) please' })]);
    const { w } = open();
    await flushPromises();

    const chip = w.find('[data-mention="2"]');
    expect(chip.exists()).toBe(true);
    expect(chip.text()).toBe('@Grace Hopper');
  });

  it('falls back to the captured name for somebody no longer in the roster', async () => {
    apiMock.listComments.mockResolvedValue([comment({ content: 'ping @[Departed](99)' })]);
    const { w } = open();
    await flushPromises();

    expect(w.find('[data-mention="99"]').text()).toBe('@Departed');
  });

  it('never renders a comment body as markup', async () => {
    // Segments are Vue nodes, not v-html. A comment must not be able to
    // introduce elements into the page.
    apiMock.listComments.mockResolvedValue([comment({ content: '<img src=x onerror=alert(1)>' })]);
    const { w } = open();
    await flushPromises();

    expect(w.find('[data-comment="1"] img').exists()).toBe(false);
    expect(w.find('[data-comment="1"]').text()).toContain('<img src=x onerror=alert(1)>');
  });
});

describe('CommentThread — replies', () => {
  function open() {
    let store!: Store;
    const w = mountWithPinia(CommentThread, {
      props: { taskId: 'TSK-10' },
      setup: () => {
        store = useTaskStore();
        store.currentUser = { id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any;
        store.projects = [fakeProject()] as any;
        store.currentProjectId = 1;
        store.isBackendConnected = true;
        store.members = [roster()] as any;
      },
    });
    return { w, store };
  }

  it('nests a reply under its parent, not as a sibling', async () => {
    apiMock.listComments.mockResolvedValue([
      comment({ id: 1, content: 'Original' }),
      comment({ id: 2, content: 'A reply', parent_id: 1 }),
    ]);
    const { w } = open();
    await flushPromises();

    // One thread, containing both.
    expect(w.findAll('[data-thread]')).toHaveLength(1);
    expect(w.find('[data-thread="1"] [data-comment="2"]').attributes('data-reply')).toBe('true');
  });

  it('shows who is being replied to before you send', async () => {
    apiMock.listComments.mockResolvedValue([comment({ id: 1, content: 'Original' })]);
    const { w } = open();
    await flushPromises();

    await w.find('[data-reply-to="1"]').trigger('click');
    await flushPromises();

    expect(w.find('#reply-banner').text()).toContain('Ada Lovelace');
    expect(w.find('#reply-banner').text()).toContain('Original');
  });

  it('sends the parent id', async () => {
    apiMock.listComments.mockResolvedValue([comment({ id: 1, content: 'Original' })]);
    const { w } = open();
    await flushPromises();
    await w.find('[data-reply-to="1"]').trigger('click');

    await w.find('#comment-draft').setValue('Agreed');
    await w.findAll('button').find((b: any) => /^post$/i.test(b.text()))!.trigger('click');
    await flushPromises();

    expect(apiMock.addComment).toHaveBeenCalledWith(10, 'Agreed', 'COMMENT', 1);
  });

  it('cancelling returns to a top-level comment', async () => {
    apiMock.listComments.mockResolvedValue([comment({ id: 1, content: 'Original' })]);
    const { w } = open();
    await flushPromises();
    await w.find('[data-reply-to="1"]').trigger('click');

    await w.find('#reply-cancel').trigger('click');
    await flushPromises();

    expect(w.find('#reply-banner').exists()).toBe(false);
  });

  it('clears the reply target after posting, so the next note is not a reply too', async () => {
    apiMock.listComments.mockResolvedValue([comment({ id: 1, content: 'Original' })]);
    const { w } = open();
    await flushPromises();
    await w.find('[data-reply-to="1"]').trigger('click');
    await w.find('#comment-draft').setValue('Agreed');
    await w.findAll('button').find((b: any) => /^post$/i.test(b.text()))!.trigger('click');
    await flushPromises();

    expect(w.find('#reply-banner').exists()).toBe(false);
  });

  it('offers Reply on a reply too, since the server flattens it', async () => {
    apiMock.listComments.mockResolvedValue([
      comment({ id: 1, content: 'Original' }),
      comment({ id: 2, content: 'A reply', parent_id: 1 }),
    ]);
    const { w } = open();
    await flushPromises();

    expect(w.find('[data-reply-to="2"]').exists()).toBe(true);
  });
});

describe('CommentThread — paste', () => {
  function open() {
    let store!: Store;
    const w = mountWithPinia(CommentThread, {
      props: { taskId: 'TSK-10' },
      setup: () => {
        store = useTaskStore();
        store.currentUser = { id: 1, email: 'a@b.c', full_name: 'Ada', skills: '' } as any;
        store.projects = [fakeProject()] as any;
        store.currentProjectId = 1;
        store.isBackendConnected = true;
        store.members = [roster()] as any;
      },
    });
    return { w, store };
  }

  it('queues a pasted image like a chosen one', async () => {
    const { w } = open();
    await flushPromises();

    const box = w.find('#comment-draft').element;
    box.dispatchEvent(pasteEvent([new File(['x'], 'image.png', { type: 'image/png' })]));
    await w.vm.$nextTick();

    expect(w.findAll('[data-pending-file]')).toHaveLength(1);
  });

  it('names a screenshot from the timestamp, since the clipboard gives none', async () => {
    const { w } = open();
    await flushPromises();

    const box = w.find('#comment-draft').element;
    box.dispatchEvent(pasteEvent([new File(['x'], 'image.png', { type: 'image/png' })]));
    await w.vm.$nextTick();

    expect(w.find('[data-pending-file]').text()).toMatch(/pasted-.*\.png/);
  });

  it('keeps a real filename when the clipboard supplies one', async () => {
    const { w } = open();
    await flushPromises();

    const box = w.find('#comment-draft').element;
    box.dispatchEvent(pasteEvent([new File(['x'], 'diagram.png', { type: 'image/png' })]));
    await w.vm.$nextTick();

    expect(w.find('[data-pending-file]').text()).toContain('diagram.png');
  });

  it('numbers several images pasted at once', async () => {
    const { w } = open();
    await flushPromises();

    const box = w.find('#comment-draft').element;
    box.dispatchEvent(pasteEvent([
      new File(['a'], 'image.png', { type: 'image/png' }),
      new File(['b'], 'image.png', { type: 'image/png' }),
    ]));
    await w.vm.$nextTick();

    const names = w.findAll('[data-pending-file]').map((n: any) => n.text());
    expect(names).toHaveLength(2);
    expect(names[0]).not.toBe(names[1]);
  });

  it('leaves a plain-text paste entirely to the browser', async () => {
    // Intercepting text would break the caret and the undo stack for no gain.
    const { w } = open();
    await flushPromises();

    const ev: any = new Event('paste', { bubbles: true, cancelable: true });
    ev.clipboardData = { items: [{ kind: 'string', getAsFile: () => null }] };
    w.find('#comment-draft').element.dispatchEvent(ev);
    await w.vm.$nextTick();

    expect(ev.defaultPrevented).toBe(false);
    expect(w.findAll('[data-pending-file]')).toHaveLength(0);
  });
});
