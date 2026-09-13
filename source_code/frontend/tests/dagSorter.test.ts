import { describe, it, expect } from 'vitest';
import { topologicalSort, computeCriticalPath } from '../src/lib/dagSorter';
import type { Task } from '../src/types/task';

describe('DAG Sorter & Critical Path Engine', () => {
  const baseTask = (id: string, partial: Partial<Task> = {}): Task => ({
    id,
    title: `Task ${id}`,
    status: 'TODO',
    priority: 'MEDIUM',
    complexity: 'M',
    createdAt: 1000,
    updatedAt: 1000,
    ...partial,
  });

  describe('topologicalSort', () => {
    it('sorts dependent tasks so prerequisites appear before dependents', () => {
      const tasks: Task[] = [
        baseTask('TSK-3', { dependencies: ['TSK-2'] }),
        baseTask('TSK-1'),
        baseTask('TSK-2', { dependencies: ['TSK-1'] }),
      ];

      const sorted = topologicalSort(tasks);
      const ids = sorted.map((t) => t.id);

      expect(ids.indexOf('TSK-1')).toBeLessThan(ids.indexOf('TSK-2'));
      expect(ids.indexOf('TSK-2')).toBeLessThan(ids.indexOf('TSK-3'));
      expect(sorted.length).toBe(3);
    });

    it('safely handles circular dependencies without infinite looping or dropping tasks', () => {
      const cyclicTasks: Task[] = [
        baseTask('TSK-A', { dependencies: ['TSK-B'] }),
        baseTask('TSK-B', { dependencies: ['TSK-A'] }),
        baseTask('TSK-C'),
      ];

      const sorted = topologicalSort(cyclicTasks);
      expect(sorted.length).toBe(3);
      expect(sorted.map((t) => t.id)).toContain('TSK-A');
      expect(sorted.map((t) => t.id)).toContain('TSK-B');
      expect(sorted.map((t) => t.id)).toContain('TSK-C');
    });

    it('orders independent tasks by priority weight', () => {
      const tasks: Task[] = [
        baseTask('TSK-LOW', { priority: 'LOW' }),
        baseTask('TSK-CRIT', { priority: 'CRITICAL' }),
        baseTask('TSK-HIGH', { priority: 'HIGH' }),
      ];

      const sorted = topologicalSort(tasks);
      expect(sorted[0].id).toBe('TSK-CRIT');
      expect(sorted[1].id).toBe('TSK-HIGH');
      expect(sorted[2].id).toBe('TSK-LOW');
    });
  });

  describe('computeCriticalPath', () => {
    it('identifies the heaviest dependency chain as the critical path', () => {
      const tasks: Task[] = [
        baseTask('TSK-1', { priority: 'HIGH', complexity: 'L' }), // weight: 5 * 5 = 25
        baseTask('TSK-2', { priority: 'CRITICAL', complexity: 'XL', dependencies: ['TSK-1'] }), // weight: 10 * 8 = 80 (+ 25 = 105)
        baseTask('TSK-3', { priority: 'LOW', complexity: 'S' }), // weight: 1 * 1 = 1
      ];

      const critPath = computeCriticalPath(tasks);
      expect(critPath.has('TSK-1')).toBe(true);
      expect(critPath.has('TSK-2')).toBe(true);
      expect(critPath.has('TSK-3')).toBe(false);
    });

    it('excludes completed (DONE) tasks from critical path calculation', () => {
      const tasks: Task[] = [
        baseTask('TSK-1', { status: 'DONE', priority: 'CRITICAL', complexity: 'XL' }),
        baseTask('TSK-2', { status: 'TODO', priority: 'HIGH', complexity: 'M' }),
      ];

      const critPath = computeCriticalPath(tasks);
      expect(critPath.has('TSK-1')).toBe(false);
      expect(critPath.has('TSK-2')).toBe(true);
    });
  });
});
