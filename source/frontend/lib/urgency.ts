import type { Task } from '../types/task';

/**
 * Deadline urgency, and the board's default ordering.
 *
 * Split out as a pure module rather than living inside the store getter so the
 * ordering rules can be tested directly — the store getter would drag in Pinia,
 * IndexedDB and the API client to assert a comparison.
 *
 * `now` is always a parameter, never `Date.now()` read internally. A function
 * whose result depends on the wall clock cannot be tested at a boundary, and
 * "is this overdue?" is nothing but boundaries.
 */

export type UrgencyLevel = 'OVERDUE' | 'TODAY' | 'SOON' | 'LATER' | 'NONE';

/** Tasks due within this many days count as SOON. */
export const SOON_DAYS = 3;

const DAY_MS = 86_400_000;

/**
 * Whole days from `now` until `dueDate`, counted in local calendar days.
 *
 * Calendar days, not 24-hour blocks: something due at 09:00 tomorrow is "in 1
 * day" even when it is 23:00 now and the gap is ten hours. Users read deadlines
 * off a calendar, so the arithmetic has to as well.
 */
export function daysUntil(dueDate: string, now: number): number | null {
  const due = new Date(dueDate);
  if (Number.isNaN(due.getTime())) return null;

  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  return Math.round((startOfDay(due) - startOfDay(new Date(now))) / DAY_MS);
}

export function urgencyOf(task: Task, now: number): UrgencyLevel {
  // A finished task is never urgent, however overdue it was. Leaving DONE items
  // burning red at the top of the board is how a board stops being read.
  if (task.status === 'DONE') return 'NONE';
  if (!task.dueDate) return 'NONE';

  const days = daysUntil(task.dueDate, now);
  if (days === null) return 'NONE';
  if (days < 0) return 'OVERDUE';
  if (days === 0) return 'TODAY';
  if (days <= SOON_DAYS) return 'SOON';
  return 'LATER';
}

const URGENCY_RANK: Record<UrgencyLevel, number> = {
  OVERDUE: 0,
  TODAY: 1,
  SOON: 2,
  LATER: 3,
  NONE: 4,
};

const PRIORITY_RANK: Record<Task['priority'], number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

/**
 * The board's default order: what needs attention first.
 *
 *   1. Urgency band — overdue, then today, then soon, then dated, then undated.
 *   2. Within a band, the earlier deadline.
 *   3. Then priority, so an undated CRITICAL still outranks an undated LOW.
 *   4. Then newest first, which is the order the board had before.
 *
 * Deadline outranks priority deliberately. A LOW task due yesterday is a
 * broken promise; a CRITICAL one due next month is not yet a problem. Priority
 * is a statement about importance, a deadline is a statement about time, and
 * only one of them is running out.
 *
 * Returns a new array — Array.prototype.sort mutates, and this runs inside a
 * getter over the store's own state.
 */
export function sortByUrgency(tasks: Task[], now: number): Task[] {
  return [...tasks].sort((a, b) => {
    const ua = URGENCY_RANK[urgencyOf(a, now)];
    const ub = URGENCY_RANK[urgencyOf(b, now)];
    if (ua !== ub) return ua - ub;

    if (a.dueDate && b.dueDate) {
      const diff = new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
      if (diff !== 0) return diff;
    }

    const pa = PRIORITY_RANK[a.priority];
    const pb = PRIORITY_RANK[b.priority];
    if (pa !== pb) return pa - pb;

    return b.createdAt - a.createdAt;
  });
}

/** Short human label, e.g. "3d overdue", "Today", "in 2d". */
export function dueLabel(task: Task, now: number): string | null {
  if (!task.dueDate) return null;
  const days = daysUntil(task.dueDate, now);
  if (days === null) return null;
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return 'Today';
  if (days === 1) return 'Tomorrow';
  return `in ${days}d`;
}
