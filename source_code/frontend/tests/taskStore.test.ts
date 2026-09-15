import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useTaskStore, compareTasks } from '../src/stores/taskStore';
import type { Task } from '../src/types/task';

vi.mock('idb-keyval', () => ({
  get: vi.fn().mockResolvedValue(null),
  set: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../src/services/api', () => ({
  api: {
    getToken: vi.fn().mockReturnValue(null),
    getMe: vi.fn(),
    getTasks: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    requestPriority: vi.fn(),
    approvePriority: vi.fn(),
    rejectPriority: vi.fn(),
    getSprints: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn().mockImplementation((id, updates) => Promise.resolve({ id, ...updates })),
    uploadAvatar: vi.fn().mockImplementation((file) => Promise.resolve({ avatar_url: '/api/users/42/avatar?v=12345678', avatar_file: '12345678.png' })),
  },
}));

describe('TaskStore & Multi-Key Comparator', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

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

  describe('compareTasks (Multi-Key Sorting)', () => {
    it('prioritizes active critical path tasks above all else', () => {
      const critSet = new Set(['TSK-102']);
      const t1 = baseTask('TSK-101', { priority: 'CRITICAL', status: 'TODO' });
      const t2 = baseTask('TSK-102', { priority: 'LOW', status: 'TODO' });

      // t2 is on critical path, so it comes first despite lower priority
      expect(compareTasks(t1, t2, critSet)).toBeGreaterThan(0);
      expect(compareTasks(t2, t1, critSet)).toBeLessThan(0);
    });

    it('does not prioritize DONE critical path tasks', () => {
      const critSet = new Set(['TSK-102']);
      const t1 = baseTask('TSK-101', { priority: 'CRITICAL', status: 'TODO' });
      const t2 = baseTask('TSK-102', { priority: 'LOW', status: 'DONE' });

      expect(compareTasks(t1, t2, critSet)).toBeLessThan(0);
    });

    it('sorts by priority when critical path status is equal', () => {
      const crit = baseTask('TSK-1', { priority: 'CRITICAL' });
      const high = baseTask('TSK-2', { priority: 'HIGH' });
      const med = baseTask('TSK-3', { priority: 'MEDIUM' });
      const low = baseTask('TSK-4', { priority: 'LOW' });

      expect(compareTasks(crit, high)).toBeLessThan(0);
      expect(compareTasks(high, med)).toBeLessThan(0);
      expect(compareTasks(med, low)).toBeLessThan(0);
    });

    it('sorts by due date ascending when priority is equal', () => {
      const early = baseTask('TSK-1', { priority: 'HIGH', dueDate: '2026-10-01T00:00:00Z' });
      const late = baseTask('TSK-2', { priority: 'HIGH', dueDate: '2026-10-15T00:00:00Z' });
      const noDue = baseTask('TSK-3', { priority: 'HIGH' });

      expect(compareTasks(early, late)).toBeLessThan(0);
      expect(compareTasks(late, noDue)).toBeLessThan(0);
      expect(compareTasks(early, noDue)).toBeLessThan(0);
    });

    it('falls back to stable numerical / compact ID comparison', () => {
      const t101 = baseTask('TSK-101', { priority: 'MEDIUM' });
      const t102 = baseTask('TSK-102', { priority: 'MEDIUM' });
      const tTemp = baseTask('TSK-T105', { priority: 'MEDIUM' });

      expect(compareTasks(t101, t102)).toBeLessThan(0);
      expect(compareTasks(t102, tTemp)).toBeLessThan(0);
    });
  });

  describe('Compact ID Creation & Store Operations', () => {
    it('creates new task with compact temporary ID based on highest existing ID', () => {
      const store = useTaskStore();
      store.tasks = [
        baseTask('TSK-101'),
        baseTask('TSK-102'),
      ];

      const created = store.createTask('Implement Feature X', 'HIGH');
      expect(created).not.toBeNull();
      expect(created?.id).toBe('TSK-T103');
      expect(created?.title).toBe('Implement Feature X');
      expect(created?.priority).toBe('HIGH');
      expect(store.tasks[0].id).toBe('TSK-T103');
    });

    it('returns null if title is blank', () => {
      const store = useTaskStore();
      const created = store.createTask('   ');
      expect(created).toBeNull();
    });

    it('filters tasks by sprintId (ALL, specific sprint, BACKLOG)', () => {
      const store = useTaskStore();
      store.tasks = [
        baseTask('TSK-1', { sprintId: 1 }),
        baseTask('TSK-2', { sprintId: 2 }),
        baseTask('TSK-3', { sprintId: null }),
      ];

      store.filter.sprintId = 'ALL';
      expect(store.filteredTasks.map((t) => t.id)).toEqual(expect.arrayContaining(['TSK-1', 'TSK-2', 'TSK-3']));

      store.setFilterSprint(1);
      expect(store.filteredTasks.map((t) => t.id)).toEqual(['TSK-1']);

      store.setFilterSprint('BACKLOG');
      expect(store.filteredTasks.map((t) => t.id)).toEqual(['TSK-3']);
    });

    it('handles priority change requests, approvals, and rejections', async () => {
      const store = useTaskStore();
      store.tasks = [
        baseTask('TSK-100', { priority: 'LOW' }),
      ];

      // 1. Member requests priority change
      await store.requestPriorityChange('TSK-100', 'CRITICAL', 'Urgent blocker');
      expect(store.tasks[0].requestedPriority).toBe('CRITICAL');
      expect(store.tasks[0].priorityRequestReason).toBe('Urgent blocker');
      expect(store.tasks[0].priority).toBe('LOW');

      // 2. Reject change
      await store.rejectPriorityChange('TSK-100');
      expect(store.tasks[0].requestedPriority).toBeNull();
      expect(store.tasks[0].priorityRequestReason).toBeNull();
      expect(store.tasks[0].priority).toBe('LOW');

      // 3. Request and Approve
      await store.requestPriorityChange('TSK-100', 'HIGH', 'Upgraded priority');
      await store.approvePriorityChange('TSK-100');
      expect(store.tasks[0].priority).toBe('HIGH');
      expect(store.tasks[0].requestedPriority).toBeNull();
      expect(store.tasks[0].priorityRequestReason).toBeNull();
    });

    it('manages appView state transitions (LANDING, BOARD, PROFILE)', async () => {
      const store = useTaskStore();
      // Without token in mock, defaults to LANDING
      expect(store.appView).toBe('LANDING');

      store.setAppView('BOARD');
      expect(store.appView).toBe('BOARD');

      store.setAppView('PROFILE');
      expect(store.appView).toBe('PROFILE');

      store.logout();
      expect(store.appView).toBe('LANDING');
    });

    it('updates user profile information reactively', async () => {
      const store = useTaskStore();
      store.currentUser = {
        id: 42,
        email: 'dev@koshi.io',
        full_name: 'Original Name',
        role: 'MEMBER',
        skills: 'javascript'
      };

      await store.updateCurrentUser({
        full_name: 'Updated Name',
        skills: 'vue,pinia,typescript'
      });

      expect(store.currentUser.full_name).toBe('Updated Name');
      expect(store.currentUser.skills).toBe('vue,pinia,typescript');
    });
  });
});
