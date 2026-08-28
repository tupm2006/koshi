/**
 * Tests for the dependency graph engine (D5 GAP-01).
 *
 * These are characterisation tests: they pin down what `dagSorter.ts` actually
 * does today, verified against the current implementation rather than against
 * an idealised spec. Where behaviour is surprising it is asserted and labelled,
 * not silently corrected — see D6 P4/P5.
 *
 * Covers D1 FR-GRAPH-01..04 and D4 INV-04, INV-05.
 */
import { describe, it, expect } from 'vitest';
import { topologicalSort, computeCriticalPath } from './dagSorter';
import type { Task, TaskPriority, Complexity } from '../types/task';

let seq = 0;

function task(id: string, overrides: Partial<Task> = {}): Task {
  seq += 1;
  return {
    id,
    title: `Task ${id}`,
    status: 'TODO',
    priority: 'MEDIUM',
    createdAt: seq * 1000,
    updatedAt: seq * 1000,
    ...overrides,
  };
}

const ids = (tasks: Task[]) => tasks.map((t) => t.id);
const indexOf = (tasks: Task[], id: string) => ids(tasks).indexOf(id);

// ---------------------------------------------------------------------------
// topologicalSort — ordering (FR-GRAPH-01)
// ---------------------------------------------------------------------------

describe('topologicalSort — dependency ordering', () => {
  it('returns an empty array for empty input', () => {
    expect(topologicalSort([])).toEqual([]);
  });

  it('places a dependency before its dependent', () => {
    const a = task('A');
    const b = task('B', { dependencies: ['A'] });

    // Deliberately supplied in the wrong order.
    const sorted = topologicalSort([b, a]);

    expect(indexOf(sorted, 'A')).toBeLessThan(indexOf(sorted, 'B'));
  });

  it('orders a three-link chain end to end', () => {
    const a = task('A');
    const b = task('B', { dependencies: ['A'] });
    const c = task('C', { dependencies: ['B'] });

    expect(ids(topologicalSort([c, b, a]))).toEqual(['A', 'B', 'C']);
  });

  it('resolves a diamond so both middles precede the join', () => {
    const a = task('A');
    const b = task('B', { dependencies: ['A'] });
    const c = task('C', { dependencies: ['A'] });
    const d = task('D', { dependencies: ['B', 'C'] });

    const sorted = topologicalSort([d, c, b, a]);

    expect(indexOf(sorted, 'A')).toBe(0);
    expect(indexOf(sorted, 'D')).toBe(3);
    expect(indexOf(sorted, 'B')).toBeLessThan(indexOf(sorted, 'D'));
    expect(indexOf(sorted, 'C')).toBeLessThan(indexOf(sorted, 'D'));
  });

  it('preserves every task exactly once', () => {
    const tasks = [
      task('A'),
      task('B', { dependencies: ['A'] }),
      task('C'),
      task('D', { dependencies: ['A', 'C'] }),
    ];

    const sorted = topologicalSort(tasks);

    expect(sorted).toHaveLength(tasks.length);
    expect(new Set(ids(sorted)).size).toBe(tasks.length);
  });

  it('ignores dependencies on ids that are not in the set', () => {
    // The board is frequently filtered, so a dependency can reference a task
    // that is not in the current slice. That must not drop or reorder anything.
    const a = task('A', { dependencies: ['GHOST-1', 'GHOST-2'] });

    expect(ids(topologicalSort([a]))).toEqual(['A']);
  });
});

// ---------------------------------------------------------------------------
// topologicalSort — deterministic tie-breaking (FR-GRAPH-02)
// ---------------------------------------------------------------------------

describe('topologicalSort — tie-breaking', () => {
  it('orders independent tasks by priority, highest first', () => {
    const low = task('LOW', { priority: 'LOW' });
    const critical = task('CRIT', { priority: 'CRITICAL' });
    const medium = task('MED', { priority: 'MEDIUM' });
    const high = task('HIGH', { priority: 'HIGH' });

    expect(ids(topologicalSort([low, medium, high, critical])))
      .toEqual(['CRIT', 'HIGH', 'MED', 'LOW']);
  });

  it('falls back to the earlier due date when priorities match', () => {
    const later = task('LATER', { dueDate: '2026-09-10T00:00:00.000Z' });
    const sooner = task('SOONER', { dueDate: '2026-09-01T00:00:00.000Z' });

    expect(ids(topologicalSort([later, sooner]))).toEqual(['SOONER', 'LATER']);
  });

  it('falls back to creation time when priority and due dates match', () => {
    const older = task('OLDER', { createdAt: 1_000 });
    const newer = task('NEWER', { createdAt: 9_000 });

    expect(ids(topologicalSort([newer, older]))).toEqual(['OLDER', 'NEWER']);
  });

  it('priority outranks an earlier due date', () => {
    const urgentDate = task('SOON_LOW', { priority: 'LOW', dueDate: '2026-09-01T00:00:00.000Z' });
    const important = task('LATE_CRIT', { priority: 'CRITICAL', dueDate: '2026-12-31T00:00:00.000Z' });

    expect(ids(topologicalSort([urgentDate, important]))).toEqual(['LATE_CRIT', 'SOON_LOW']);
  });

  it('QUIRK: due date is only consulted when BOTH tasks have one', () => {
    // The comparator guards on `taskA.dueDate && taskB.dueDate`, so a task with
    // a due date does not sort ahead of one without — it silently falls through
    // to createdAt. Asserted so the behaviour is a decision, not an accident.
    const dated = task('DATED', { createdAt: 9_000, dueDate: '2026-09-01T00:00:00.000Z' });
    const undated = task('UNDATED', { createdAt: 1_000 });

    expect(ids(topologicalSort([dated, undated]))).toEqual(['UNDATED', 'DATED']);
  });

  it('is deterministic across repeated runs and input permutations', () => {
    const build = () => [
      task('A', { priority: 'HIGH' }),
      task('B', { priority: 'HIGH', dependencies: ['A'] }),
      task('C', { priority: 'LOW' }),
      task('D', { priority: 'CRITICAL' }),
    ];

    const base = ids(topologicalSort(build()));

    // Same tasks, shuffled input, must produce the same order.
    for (const permute of [
      (t: Task[]) => [t[3], t[2], t[1], t[0]],
      (t: Task[]) => [t[1], t[3], t[0], t[2]],
      (t: Task[]) => [t[2], t[0], t[3], t[1]],
    ]) {
      seq = 0;
      const shuffled = permute(build());
      expect(ids(topologicalSort(shuffled))).toEqual(base);
    }
  });
});

// ---------------------------------------------------------------------------
// topologicalSort — cycle tolerance (FR-GRAPH-03, INV-04)
// ---------------------------------------------------------------------------

describe('topologicalSort — cycles degrade gracefully', () => {
  it('returns every task of a 3-cycle without throwing or hanging', () => {
    // D7/DEC-002: the retired SRS specified raising CycleDetectedException.
    // The engine feeds the primary render path, so it degrades instead —
    // blanking the board over unfixable data would be worse.
    const a = task('A', { dependencies: ['C'] });
    const b = task('B', { dependencies: ['A'] });
    const c = task('C', { dependencies: ['B'] });

    const sorted = topologicalSort([a, b, c]);

    expect(sorted).toHaveLength(3);
    expect(new Set(ids(sorted))).toEqual(new Set(['A', 'B', 'C']));
  });

  it('tolerates a task that depends on itself', () => {
    const a = task('A', { dependencies: ['A'] });

    expect(ids(topologicalSort([a]))).toEqual(['A']);
  });

  it('sorts the acyclic part first and appends cycle members after it', () => {
    const clean = task('CLEAN');
    const x = task('X', { dependencies: ['Y'] });
    const y = task('Y', { dependencies: ['X'] });

    const sorted = topologicalSort([x, y, clean]);

    expect(sorted).toHaveLength(3);
    // The resolvable task is emitted by Kahn's algorithm; the cycle members are
    // appended afterwards in their original input order.
    expect(sorted[0].id).toBe('CLEAN');
    expect(ids(sorted).slice(1)).toEqual(['X', 'Y']);
  });
});

// ---------------------------------------------------------------------------
// computeCriticalPath (FR-GRAPH-04, INV-05)
// ---------------------------------------------------------------------------

const withWeight = (id: string, priority: TaskPriority, complexity: Complexity, rest: Partial<Task> = {}) =>
  task(id, { priority, complexity, ...rest });

describe('computeCriticalPath', () => {
  it('returns an empty set for no tasks', () => {
    expect(computeCriticalPath([])).toEqual(new Set());
  });

  it('returns the only task when there is just one', () => {
    expect(computeCriticalPath([task('A')])).toEqual(new Set(['A']));
  });

  it('returns the whole chain, not just its endpoint', () => {
    const a = withWeight('A', 'LOW', 'S');
    const b = withWeight('B', 'CRITICAL', 'XL', { dependencies: ['A'] });
    const standalone = withWeight('C', 'HIGH', 'L');

    // A = 1x1 = 1; B = 10x8 = 80, chain A->B = 81; C = 5x5 = 25.
    expect(computeCriticalPath([a, b, standalone])).toEqual(new Set(['A', 'B']));
  });

  it('weights a chain above a heavier single task', () => {
    const heavy = withWeight('HEAVY', 'CRITICAL', 'M'); // 10 x 3 = 30
    const c1 = withWeight('C1', 'HIGH', 'L'); //  5 x 5 = 25
    const c2 = withWeight('C2', 'HIGH', 'M', { dependencies: ['C1'] }); // 5 x 3 = 15, chain = 40

    expect(computeCriticalPath([heavy, c1, c2])).toEqual(new Set(['C1', 'C2']));
  });

  it('uses the CPM complexity scale (S1/M3/L5/XL8), not the storage scale', () => {
    // D4 §3.2: two scales coexist deliberately. Under the CPM scale a single M
    // (2x3=6) beats a chain of two S (2x1 + 2x1 = 4). Under the storage scale
    // (M=2) the two would tie at 4, and because the comparison is a strict `>`
    // the chain — listed first — would win instead. Asserting {M} therefore
    // pins the CPM scale specifically.
    const s1 = withWeight('S1', 'MEDIUM', 'S');
    const s2 = withWeight('S2', 'MEDIUM', 'S', { dependencies: ['S1'] });
    const m = withWeight('M', 'MEDIUM', 'M');

    expect(computeCriticalPath([s1, s2, m])).toEqual(new Set(['M']));
  });

  it('uses the CPM priority scale, so complexity can outweigh priority', () => {
    // CRITICAL x S = 10 x 1 = 10, but HIGH x M = 5 x 3 = 15.
    const criticalButTiny = withWeight('CRIT_S', 'CRITICAL', 'S');
    const highButBigger = withWeight('HIGH_M', 'HIGH', 'M');

    expect(computeCriticalPath([criticalButTiny, highButBigger])).toEqual(new Set(['HIGH_M']));
  });

  it('defaults missing complexity to M', () => {
    // No complexity set: 5 x 3 = 15, which must beat HIGH x S = 5 x 1 = 5.
    const noComplexity = task('DEFAULT', { priority: 'HIGH' });
    const small = withWeight('SMALL', 'HIGH', 'S');

    expect(computeCriticalPath([noComplexity, small])).toEqual(new Set(['DEFAULT']));
  });

  it('excludes DONE tasks entirely (INV-05)', () => {
    const done = withWeight('DONE_HUGE', 'CRITICAL', 'XL', { status: 'DONE' });
    const active = withWeight('ACTIVE', 'LOW', 'S');

    const result = computeCriticalPath([done, active]);

    expect(result.has('DONE_HUGE')).toBe(false);
    expect(result).toEqual(new Set(['ACTIVE']));
  });

  it('a completed dependency breaks the chain rather than extending it', () => {
    // Finished work is no longer on the critical path, so the chain restarts.
    const a = withWeight('A', 'CRITICAL', 'XL', { status: 'DONE' });
    const b = withWeight('B', 'LOW', 'S', { dependencies: ['A'] });
    const c = withWeight('C', 'HIGH', 'M');

    const result = computeCriticalPath([a, b, c]);

    expect(result.has('A')).toBe(false);
    // B is 1x1 = 1 with its only dependency gone; C is 5x3 = 15.
    expect(result).toEqual(new Set(['C']));
  });

  it('ignores dependencies on ids outside the set', () => {
    const a = withWeight('A', 'HIGH', 'M', { dependencies: ['GHOST'] });

    expect(computeCriticalPath([a])).toEqual(new Set(['A']));
  });

  it('terminates on a cycle instead of recursing forever', () => {
    const a = withWeight('A', 'HIGH', 'M', { dependencies: ['B'] });
    const b = withWeight('B', 'HIGH', 'M', { dependencies: ['A'] });

    const result = computeCriticalPath([a, b]);

    // The visited-set guard truncates the revisit, so a finite path comes back.
    expect(result.size).toBeGreaterThan(0);
    expect(result.size).toBeLessThanOrEqual(2);
  });

  it('KNOWN LIMITATION: on cyclic graphs the result depends on input order', () => {
    // `getPathWeight` memoises by task id alone, but its result also depends on
    // the `visited` set that truncated the walk. In a cyclic graph a node can be
    // memoised from a partially-truncated traversal and then reused where the
    // truncation would not have applied, so the same graph yields different
    // answers depending on the order tasks happen to arrive in.
    //
    // Acyclic graphs are unaffected: nothing truncates, so the memo is sound.
    // This is asserted rather than fixed so the defect is visible and pinned —
    // if someone repairs it, this test fails loudly and the docs get updated.
    // Tracked as D7 / F-24.
    const b = withWeight('B', 'HIGH', 'M', { dependencies: ['C'] });
    const c = withWeight('C', 'HIGH', 'M', { dependencies: ['B'] }); // B <-> C
    const e = withWeight('E', 'HIGH', 'M', { dependencies: ['C'] }); // hangs off it

    const cycleFirst = computeCriticalPath([b, c, e]);
    const dependentFirst = computeCriticalPath([e, b, c]);

    expect(cycleFirst).toEqual(new Set(['B', 'C']));
    expect(dependentFirst).toEqual(new Set(['B', 'C', 'E']));
    expect(cycleFirst).not.toEqual(dependentFirst);
  });

  it('excludes a fully completed board from the critical path', () => {
    const tasks = [
      withWeight('A', 'CRITICAL', 'XL', { status: 'DONE' }),
      withWeight('B', 'HIGH', 'L', { status: 'DONE' }),
    ];

    expect(computeCriticalPath(tasks)).toEqual(new Set());
  });
});
