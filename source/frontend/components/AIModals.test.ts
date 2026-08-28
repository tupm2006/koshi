// @vitest-environment jsdom
/**
 * Tests for the six AI / analysis modals (D5 GAP-13).
 *
 * Each modal is a thin shell over an endpoint that is already covered
 * server-side, so these tests deliberately do not re-test the AI output. What
 * they cover is the part that only exists on the client and that the server
 * cannot protect: which call is made, what happens when it fails, and — for
 * the two modals that write to the board — whether the write actually landed.
 *
 * That last point is where the bugs were.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
    createTask: vi.fn(async () => ({})),
    updateTask: vi.fn(async () => ({})),
    deleteTask: vi.fn(async () => undefined),
    decomposeGoal: vi.fn(),
    getWeeklySummary: vi.fn(),
    extractMeetingMinutes: vi.fn(),
    recommendAssignment: vi.fn(),
    getWorkloads: vi.fn(),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import AIDecomposerModal from './AIDecomposerModal.vue';
import GitDiffModal from './GitDiffModal.vue';
import DAGVisualizerModal from './DAGVisualizerModal.vue';
import WeeklySummaryModal from './WeeklySummaryModal.vue';
import MeetingMinutesModal from './MeetingMinutesModal.vue';
import WorkloadAssignModal from './WorkloadAssignModal.vue';
import { useTaskStore } from '../stores/taskStore';
import { mountWithPinia, fakeProject } from './testing';

type Store = ReturnType<typeof useTaskStore>;

/** Mount a modal against a signed-in user with one personal project. */
function openModal(component: any, seed: (s: Store) => void = () => {}, props: any = {}) {
  let store!: Store;
  const w = mountWithPinia(component, {
    props: { onClose: () => {}, ...props },
    setup: () => {
      store = useTaskStore();
      store.currentUser = { id: 1, email: 'a@b.c', full_name: 'A', skills: '' } as any;
      store.projects = [fakeProject()] as any;
      store.currentProjectId = 1;
      store.isBackendConnected = true;
      seed(store);
    },
  });
  return { w, store: store! };
}

const clickText = async (w: any, re: RegExp) => {
  const btn = w.findAll('button').find((b: any) => re.test(b.text()));
  expect(btn, `no button matching ${re}`).toBeDefined();
  await btn!.trigger('click');
  await flushPromises();
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
  apiMock.getWeeklySummary.mockResolvedValue({ status: 'ok', summary: '### Overview\n- All on track' });
  apiMock.extractMeetingMinutes.mockResolvedValue({ main_topics: [], action_items: [], key_decisions: [] });
  apiMock.getWorkloads.mockResolvedValue([]);
  apiMock.recommendAssignment.mockResolvedValue({ recommendation: null });
  apiMock.decomposeGoal.mockResolvedValue({ subtasks: [] });
});

// ---------------------------------------------------------------------------
// AIDecomposerModal — writes to the board
// ---------------------------------------------------------------------------

describe('AIDecomposerModal', () => {
  const twoSubtasks = {
    subtasks: [
      { title: 'Design the schema', priority: 'HIGH', description: 'ERD', complexity: 'M' },
      { title: 'Write the migration', priority: 'LOW', dependsOnTitles: ['Design the schema'] },
    ],
  };

  it('sends nothing until a goal is entered', async () => {
    const { w } = openModal(AIDecomposerModal);
    await clickText(w, /decompose/i);
    expect(apiMock.decomposeGoal).not.toHaveBeenCalled();
  });

  it('decomposes the typed goal', async () => {
    const { w } = openModal(AIDecomposerModal);
    await w.find('input, textarea').setValue('Ship billing');
    await clickText(w, /decompose/i);
    expect(apiMock.decomposeGoal).toHaveBeenCalledWith('Ship billing');
  });

  it('surfaces a failure instead of appearing to succeed', async () => {
    apiMock.decomposeGoal.mockRejectedValue(new Error('Decomposition engine offline'));
    const { w } = openModal(AIDecomposerModal);
    await w.find('input, textarea').setValue('Ship billing');
    await clickText(w, /decompose/i);
    expect(w.text()).toContain('Decomposition engine offline');
  });

  it('creates one task per subtask, carrying priority and description', async () => {
    apiMock.decomposeGoal.mockResolvedValue(twoSubtasks);
    const { w, store } = openModal(AIDecomposerModal);
    await w.find('input, textarea').setValue('Ship billing');
    await clickText(w, /decompose/i);
    await clickText(w, /accept|insert|add/i);

    expect(store.tasks).toHaveLength(2);
    const schema = store.tasks.find((t) => t.title === 'Design the schema')!;
    expect(schema.priority).toBe('HIGH');
    expect(schema.description).toBe('ERD');
    expect(schema.complexity).toBe('M');
  });

  it('wires dependencies by title, using the ids the store actually assigned', async () => {
    // The AI names prerequisites by title; the board addresses them by id. The
    // second pass exists to translate, and it can only run after every subtask
    // has an id — hence two passes rather than one.
    apiMock.decomposeGoal.mockResolvedValue(twoSubtasks);
    const { w, store } = openModal(AIDecomposerModal);
    await w.find('input, textarea').setValue('Ship billing');
    await clickText(w, /decompose/i);
    await clickText(w, /accept|insert|add/i);

    const schema = store.tasks.find((t) => t.title === 'Design the schema')!;
    const migration = store.tasks.find((t) => t.title === 'Write the migration')!;
    expect(migration.dependencies).toEqual([schema.id]);
    expect(schema.dependencies ?? []).toEqual([]);
  });

  it('drops a dependency on a title that was never created', async () => {
    apiMock.decomposeGoal.mockResolvedValue({
      subtasks: [{ title: 'Only task', dependsOnTitles: ['Never mentioned'] }],
    });
    const { w, store } = openModal(AIDecomposerModal);
    await w.find('input, textarea').setValue('x');
    await clickText(w, /decompose/i);
    await clickText(w, /accept|insert|add/i);

    // A dangling id would break the DAG walk, so an unresolvable title is
    // dropped rather than passed through.
    expect(store.tasks[0]!.dependencies ?? []).toEqual([]);
  });

  it('refuses to insert into a read-only project, and says so', async () => {
    // F-33. The store gate (INV-15) blocks every createTask, so nothing is
    // written — but the modal used to flash "Inserted!" and close anyway,
    // telling the user their subtasks had been saved when none had.
    apiMock.decomposeGoal.mockResolvedValue(twoSubtasks);
    const { w, store } = openModal(AIDecomposerModal, (s) => {
      s.projects = [fakeProject({ member_count: 4 })] as any;
      s.isBackendConnected = false;
    });
    await w.find('input, textarea').setValue('Ship billing');
    await clickText(w, /decompose/i);
    await clickText(w, /accept|insert|add/i);

    expect(store.tasks).toHaveLength(0);
    expect(w.text().toLowerCase()).toMatch(/read-only|offline/);
    expect(w.emitted('close')).toBeFalsy();
  });
});

// ---------------------------------------------------------------------------
// GitDiffModal — also writes to the board
// ---------------------------------------------------------------------------

describe('GitDiffModal', () => {
  const seedTasks = (s: Store) => {
    s.createTask('Implement the parser');
    s.createTask('Write the docs');
  };

  it('analyses the pasted diff and lists the tasks it would close', async () => {
    const { w, store } = openModal(GitDiffModal, seedTasks);
    const id = store.tasks[0]!.id;
    await w.find('textarea').setValue(`fix: parser\ncloses #${id}`);
    await clickText(w, /analyze/i);

    expect(w.text()).toContain(id);
    expect(w.text()).toContain('fix: parser');
  });

  it('does not touch the board until the transitions are applied', async () => {
    const { w, store } = openModal(GitDiffModal, seedTasks);
    const id = store.tasks[0]!.id;
    await w.find('textarea').setValue(`closes #${id}`);
    await clickText(w, /analyze/i);

    expect(store.tasks[0]!.status).toBe('TODO');
  });

  it('marks exactly the resolved tasks DONE when applied', async () => {
    const { w, store } = openModal(GitDiffModal, seedTasks);
    const id = store.tasks[0]!.id;
    await w.find('textarea').setValue(`closes #${id}`);
    await clickText(w, /analyze/i);
    await clickText(w, /apply/i);

    expect(store.tasks.find((t) => t.id === id)!.status).toBe('DONE');
    expect(store.tasks.find((t) => t.id !== id)!.status).toBe('TODO');
  });

  it('refuses to apply to a read-only project, and says so', async () => {
    // F-33 again: the same false success as the decomposer.
    const { w, store } = openModal(GitDiffModal, (s) => {
      seedTasks(s);
      s.projects = [fakeProject({ member_count: 4 })] as any;
    });
    const id = store.tasks[0]!.id;
    await w.find('textarea').setValue(`closes #${id}`);
    await clickText(w, /analyze/i);
    store.isBackendConnected = false;
    await clickText(w, /apply/i);

    expect(store.tasks.find((t) => t.id === id)!.status).toBe('TODO');
    expect(w.text().toLowerCase()).toMatch(/read-only|offline/);
  });

  it('will not analyse an empty diff', async () => {
    // Stated honestly: the protection users actually hit is the disabled
    // button. `handleAnalyze` also guards on a blank diff, but that branch is
    // unreachable through the UI, so a mutation removing it survives this
    // suite. Asserting the disabled attribute is the true statement; claiming
    // the handler guard is covered would not be.
    const { w } = openModal(GitDiffModal, seedTasks);
    await w.find('textarea').setValue('   ');

    const analyze = w.findAll('button').find((b: any) => /analyze/i.test(b.text()))!;
    expect(analyze.attributes('disabled')).toBeDefined();
    await analyze.trigger('click');
    await flushPromises();
    expect(w.text()).not.toContain('Analyzed');
  });
});

// ---------------------------------------------------------------------------
// DAGVisualizerModal — read-only view over store getters
// ---------------------------------------------------------------------------

describe('DAGVisualizerModal', () => {
  it('lists tasks in topological order, prerequisites first', async () => {
    const { w, store } = openModal(DAGVisualizerModal, (s) => {
      const first = s.createTask('Design the schema')!;
      const second = s.createTask('Write the migration')!;
      s.updateTask(second.id, { dependencies: [first.id] });
    });
    await flushPromises();

    const text = w.text();
    expect(text.indexOf('Design the schema')).toBeLessThan(text.indexOf('Write the migration'));
    expect(store.dagOrder.map((t) => t.title))
      .toEqual(['Design the schema', 'Write the migration']);
  });

  it('reports the critical-path count from the store, not its own arithmetic', async () => {
    const { w, store } = openModal(DAGVisualizerModal, (s) => {
      const first = s.createTask('Design the schema')!;
      const second = s.createTask('Write the migration')!;
      s.updateTask(second.id, { dependencies: [first.id] });
    });
    await flushPromises();

    expect(w.text()).toContain(`${store.criticalPathIds.size} Bottlenecks`);
    expect(store.criticalPathIds.size).toBeGreaterThan(0);
  });

  it('renders an empty pipeline without throwing', () => {
    const { w } = openModal(DAGVisualizerModal);
    expect(w.text()).toContain('0 Bottlenecks');
  });

  it('closes from the header button', async () => {
    const { w } = openModal(DAGVisualizerModal);
    await w.findAll('button')[0]!.trigger('click');
    expect(w.emitted('close')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// WeeklySummaryModal
// ---------------------------------------------------------------------------

describe('WeeklySummaryModal', () => {
  it('requests the summary for the selected project on mount', async () => {
    openModal(WeeklySummaryModal);
    await flushPromises();
    expect(apiMock.getWeeklySummary).toHaveBeenCalledWith(1);
  });

  it('asks for a project rather than calling the API with none', async () => {
    const { w } = openModal(WeeklySummaryModal, (s) => { s.currentProjectId = null; });
    await flushPromises();

    expect(apiMock.getWeeklySummary).not.toHaveBeenCalled();
    expect(w.text()).toContain('Select a project first.');
  });

  it('renders the returned sections', async () => {
    apiMock.getWeeklySummary.mockResolvedValue({
      status: 'ok',
      summary: '### Overview\n- Sprint is on track\n### Blockers\n- Waiting on the API key',
    });
    const { w } = openModal(WeeklySummaryModal);
    await flushPromises();

    expect(w.text()).toContain('Sprint is on track');
    expect(w.text()).toContain('Waiting on the API key');
  });

  it('shows unstructured text rather than dropping it', async () => {
    // The parser splits on markdown headings; a plain-prose answer has none,
    // and must still reach the user instead of rendering as an empty panel.
    apiMock.getWeeklySummary.mockResolvedValue({ status: 'ok', summary: 'Everything is fine.' });
    const { w } = openModal(WeeklySummaryModal);
    await flushPromises();

    expect(w.text()).toContain('Everything is fine.');
  });

  it('surfaces a failure', async () => {
    apiMock.getWeeklySummary.mockRejectedValue(new Error('Summary service unavailable'));
    const { w } = openModal(WeeklySummaryModal);
    await flushPromises();

    expect(w.text()).toContain('Summary service unavailable');
  });

  it('copies the raw summary, not the reformatted panels', async () => {
    const writeText = vi.fn(async () => {});
    Object.assign(navigator, { clipboard: { writeText } });
    Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true });

    apiMock.getWeeklySummary.mockResolvedValue({ status: 'ok', summary: '### Overview\n- Fine' });
    const { w } = openModal(WeeklySummaryModal);
    await flushPromises();
    await clickText(w, /copy/i);

    expect(writeText).toHaveBeenCalledWith('### Overview\n- Fine');
  });
});

// ---------------------------------------------------------------------------
// MeetingMinutesModal
// ---------------------------------------------------------------------------

describe('MeetingMinutesModal', () => {
  it('does not call the API on mount — extraction is user-initiated', async () => {
    openModal(MeetingMinutesModal);
    await flushPromises();
    expect(apiMock.extractMeetingMinutes).not.toHaveBeenCalled();
  });

  it('sends the notes as typed', async () => {
    const { w } = openModal(MeetingMinutesModal);
    await w.find('textarea').setValue('Ada owns the migration.');
    await clickText(w, /extract/i);
    expect(apiMock.extractMeetingMinutes).toHaveBeenCalledWith('Ada owns the migration.');
  });

  it('will not send blank notes', async () => {
    const { w } = openModal(MeetingMinutesModal);
    await w.find('textarea').setValue('   ');
    await clickText(w, /extract/i);
    expect(apiMock.extractMeetingMinutes).not.toHaveBeenCalled();
  });

  it('renders topics, decisions and action items', async () => {
    apiMock.extractMeetingMinutes.mockResolvedValue({
      main_topics: ['Migration plan'],
      key_decisions: ['Ship on Friday'],
      // D4 contract: an action item is {title, assignee_name, priority} —
      // not {task, assignee}, which is the shape the endpoint's own docstring
      // suggests.
      action_items: [{ title: 'Run the migration', assignee_name: 'Ada', priority: 'HIGH' }],
    });
    const { w } = openModal(MeetingMinutesModal);
    await w.find('textarea').setValue('notes');
    await clickText(w, /extract/i);

    const text = w.text();
    expect(text).toContain('Migration plan');
    expect(text).toContain('Ship on Friday');
    expect(text).toContain('Run the migration');
    expect(text).toContain('Ada');
  });

  it('surfaces a failure', async () => {
    apiMock.extractMeetingMinutes.mockRejectedValue(new Error('Extraction failed'));
    const { w } = openModal(MeetingMinutesModal);
    await w.find('textarea').setValue('notes');
    await clickText(w, /extract/i);
    expect(w.text()).toContain('Extraction failed');
  });
});

// ---------------------------------------------------------------------------
// WorkloadAssignModal
// ---------------------------------------------------------------------------

describe('WorkloadAssignModal', () => {
  it('loads workloads and an initial recommendation on mount', async () => {
    openModal(WorkloadAssignModal);
    await flushPromises();

    expect(apiMock.getWorkloads).toHaveBeenCalledWith(1);
    expect(apiMock.recommendAssignment).toHaveBeenCalledWith(
      expect.any(String), expect.any(String), 1,
    );
  });

  it('calls nothing when no project is selected', async () => {
    openModal(WorkloadAssignModal, (s) => { s.currentProjectId = null; });
    await flushPromises();

    expect(apiMock.getWorkloads).not.toHaveBeenCalled();
    expect(apiMock.recommendAssignment).not.toHaveBeenCalled();
  });

  it('renders each member\'s workload', async () => {
    apiMock.getWorkloads.mockResolvedValue([
      { user_id: 1, full_name: 'Ada Lovelace', active_tasks: 3, total_points: 8, skills: 'python' },
    ]);
    const { w } = openModal(WorkloadAssignModal);
    await flushPromises();

    expect(w.text()).toContain('Ada Lovelace');
  });

  it('re-requests a recommendation for an edited task title', async () => {
    const { w } = openModal(WorkloadAssignModal);
    await flushPromises();
    apiMock.recommendAssignment.mockClear();

    await w.find('input').setValue('Rewrite the scheduler');
    await clickText(w, /recommend/i);

    expect(apiMock.recommendAssignment).toHaveBeenCalledWith(
      'Rewrite the scheduler', expect.any(String), 1,
    );
  });

  it('renders the recommended assignee', async () => {
    apiMock.recommendAssignment.mockResolvedValue({
      // D4 contract: recommended_name / rationale / risk_assessment.
      recommendation: {
        recommended_name: 'Ada Lovelace',
        rationale: 'Lowest current load',
        risk_assessment: 'None',
      },
    });
    const { w } = openModal(WorkloadAssignModal);
    await flushPromises();

    expect(w.text()).toContain('Ada Lovelace');
    expect(w.text()).toContain('Lowest current load');
  });

  it('does not crash when the service returns no recommendation', async () => {
    apiMock.recommendAssignment.mockResolvedValue({ recommendation: null });
    const { w } = openModal(WorkloadAssignModal);
    await flushPromises();
    expect(w.exists()).toBe(true);
  });
});
