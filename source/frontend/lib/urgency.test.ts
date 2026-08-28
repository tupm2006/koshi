import { describe, it, expect } from 'vitest';
import { daysUntil, urgencyOf, sortByUrgency, dueLabel, SOON_DAYS } from './urgency';
import type { Task } from '../types/task';

/** Midday, so a test never accidentally depends on being near midnight. */
const NOW = new Date('2026-08-28T12:00:00').getTime();

const task = (over: Partial<Task> = {}): Task => ({
  id: 'TSK-1',
  title: 'A task',
  status: 'TODO',
  priority: 'MEDIUM',
  createdAt: 0,
  updatedAt: 0,
  ...over,
});

/** A local-time ISO date `n` days from NOW. */
const inDays = (n: number) => {
  const d = new Date(NOW);
  d.setDate(d.getDate() + n);
  return d.toISOString();
};

describe('daysUntil', () => {
  it('counts calendar days, not 24-hour blocks', () => {
    // The point of the whole function. At 23:00, something due at 09:00
    // tomorrow is ten hours away but one *day* away, and that is what a user
    // reading a deadline off a calendar means.
    const lateEvening = new Date('2026-08-28T23:00:00').getTime();
    const tomorrowMorning = new Date('2026-08-29T09:00:00').toISOString();
    expect(daysUntil(tomorrowMorning, lateEvening)).toBe(1);
  });

  it('is 0 for any time today', () => {
    expect(daysUntil(new Date('2026-08-28T00:30:00').toISOString(), NOW)).toBe(0);
    expect(daysUntil(new Date('2026-08-28T23:30:00').toISOString(), NOW)).toBe(0);
  });

  it('is negative in the past', () => {
    expect(daysUntil(new Date('2026-08-25T12:00:00').toISOString(), NOW)).toBe(-3);
  });

  it('returns null for a date it cannot parse', () => {
    expect(daysUntil('not a date', NOW)).toBeNull();
  });
});

describe('urgencyOf', () => {
  it('bands a task by how long is left', () => {
    expect(urgencyOf(task({ dueDate: inDays(-1) }), NOW)).toBe('OVERDUE');
    expect(urgencyOf(task({ dueDate: inDays(0) }), NOW)).toBe('TODAY');
    expect(urgencyOf(task({ dueDate: inDays(SOON_DAYS) }), NOW)).toBe('SOON');
    expect(urgencyOf(task({ dueDate: inDays(SOON_DAYS + 1) }), NOW)).toBe('LATER');
    expect(urgencyOf(task({}), NOW)).toBe('NONE');
  });

  it('never marks a DONE task urgent, however overdue', () => {
    // Finished work is not a problem. Leaving completed tasks burning red at
    // the top of the board is how a board stops being read at all.
    expect(urgencyOf(task({ dueDate: inDays(-30), status: 'DONE' }), NOW)).toBe('NONE');
  });

  it('still marks a BLOCKED task overdue', () => {
    // Being blocked is exactly when a deadline matters most — somebody has to
    // unblock it.
    expect(urgencyOf(task({ dueDate: inDays(-2), status: 'BLOCKED' }), NOW)).toBe('OVERDUE');
  });
});

describe('sortByUrgency', () => {
  it('puts the most urgent first', () => {
    const later = task({ id: 'TSK-later', dueDate: inDays(10) });
    const overdue = task({ id: 'TSK-overdue', dueDate: inDays(-2) });
    const today = task({ id: 'TSK-today', dueDate: inDays(0) });
    const undated = task({ id: 'TSK-none' });

    expect(sortByUrgency([later, undated, today, overdue], NOW).map((t) => t.id))
      .toEqual(['TSK-overdue', 'TSK-today', 'TSK-later', 'TSK-none']);
  });

  it('orders by deadline within a band', () => {
    const a = task({ id: 'TSK-a', dueDate: inDays(-1) });
    const b = task({ id: 'TSK-b', dueDate: inDays(-5) });
    expect(sortByUrgency([a, b], NOW).map((t) => t.id)).toEqual(['TSK-b', 'TSK-a']);
  });

  it('ranks a deadline above a priority', () => {
    // The judgement call this module exists to make. A LOW task due yesterday
    // is a broken promise; a CRITICAL one due next month is not yet a problem.
    const lowOverdue = task({ id: 'TSK-low', priority: 'LOW', dueDate: inDays(-1) });
    const criticalLater = task({ id: 'TSK-crit', priority: 'CRITICAL', dueDate: inDays(30) });

    expect(sortByUrgency([criticalLater, lowOverdue], NOW).map((t) => t.id))
      .toEqual(['TSK-low', 'TSK-crit']);
  });

  it('falls back to priority when neither has a deadline', () => {
    const low = task({ id: 'TSK-low', priority: 'LOW' });
    const critical = task({ id: 'TSK-crit', priority: 'CRITICAL' });
    expect(sortByUrgency([low, critical], NOW).map((t) => t.id)).toEqual(['TSK-crit', 'TSK-low']);
  });

  it('falls back to newest first, the order the board had before', () => {
    const older = task({ id: 'TSK-old', createdAt: 1000 });
    const newer = task({ id: 'TSK-new', createdAt: 2000 });
    expect(sortByUrgency([older, newer], NOW).map((t) => t.id)).toEqual(['TSK-new', 'TSK-old']);
  });

  it('sinks a DONE task below unfinished work regardless of its deadline', () => {
    const doneOverdue = task({ id: 'TSK-done', status: 'DONE', dueDate: inDays(-9) });
    const openLater = task({ id: 'TSK-open', dueDate: inDays(20) });
    expect(sortByUrgency([doneOverdue, openLater], NOW).map((t) => t.id))
      .toEqual(['TSK-open', 'TSK-done']);
  });

  it('does not mutate its input', () => {
    const list = [task({ id: 'TSK-b', dueDate: inDays(5) }), task({ id: 'TSK-a', dueDate: inDays(1) })];
    const before = list.map((t) => t.id);
    sortByUrgency(list, NOW);
    expect(list.map((t) => t.id)).toEqual(before);
  });

  it('handles an empty list and an unparseable date', () => {
    expect(sortByUrgency([], NOW)).toEqual([]);
    const bad = task({ id: 'TSK-bad', dueDate: 'nonsense' });
    expect(sortByUrgency([bad], NOW).map((t) => t.id)).toEqual(['TSK-bad']);
  });
});

describe('dueLabel', () => {
  it('reads naturally at each distance', () => {
    expect(dueLabel(task({ dueDate: inDays(-3) }), NOW)).toBe('3d overdue');
    expect(dueLabel(task({ dueDate: inDays(0) }), NOW)).toBe('Today');
    expect(dueLabel(task({ dueDate: inDays(1) }), NOW)).toBe('Tomorrow');
    expect(dueLabel(task({ dueDate: inDays(4) }), NOW)).toBe('in 4d');
  });

  it('is null when there is no deadline to describe', () => {
    expect(dueLabel(task({}), NOW)).toBeNull();
    expect(dueLabel(task({ dueDate: 'nonsense' }), NOW)).toBeNull();
  });
});
