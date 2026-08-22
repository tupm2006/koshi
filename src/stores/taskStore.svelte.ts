import { get, set } from 'idb-keyval';
import type { Task, TaskStatus, TaskPriority, TaskFilter, FilterStatus, FilterPriority } from '../types/task';
import { topologicalSort, computeCriticalPath } from '../lib/dagSorter';
import { api, type UserProfile } from '../services/api';

const DB_KEY = 'koshi_tasks_v1';

const INITIAL_TASKS: Task[] = [
  {
    id: 'TSK-101',
    title: 'Migrate reactive state to Svelte 5 direct-DOM runes',
    description: 'Eliminate virtual-DOM diffing overhead by replacing stores with $state and $derived.',
    status: 'IN_PROGRESS',
    priority: 'CRITICAL',
    assignee: 'felixsu',
    dueDate: new Date(Date.now() + 86400000 * 2).toISOString(),
    createdAt: Date.now() - 3600000 * 8,
    updatedAt: Date.now() - 3600000 * 2,
    complexity: 'M',
    acceptanceCriteria: ['Idle RAM < 15MB', '0 runtime memory leaks', 'Zero VDOM reconciliation passes'],
  },
  {
    id: 'TSK-102',
    title: 'Implement modal-less Vim keyboard traversal engine',
    description: 'Bind j/k navigation, Space status toggle, Enter inline rename, and / quick filtering.',
    status: 'TODO',
    priority: 'HIGH',
    assignee: 'felixsu',
    dueDate: new Date(Date.now() + 86400000 * 3).toISOString(),
    createdAt: Date.now() - 3600000 * 7,
    updatedAt: Date.now() - 3600000 * 2,
    dependencies: ['TSK-101'],
    complexity: 'L',
    acceptanceCriteria: ['Interaction latency < 50ms', 'Full keyboard navigation with active selection'],
  },
  {
    id: 'TSK-103',
    title: 'Build local-first IndexedDB persistence layer',
    description: 'Ensure offline zero-latency execution with background non-blocking persistence.',
    status: 'DONE',
    priority: 'HIGH',
    assignee: 'felixsu',
    createdAt: Date.now() - 3600000 * 24,
    updatedAt: Date.now() - 3600000 * 12,
    complexity: 'S',
    acceptanceCriteria: ['Tasks load instantly on startup', 'No UI thread blocking on writes'],
  },
  {
    id: 'TSK-104',
    title: 'Topological DAG dependency sorter & critical path evaluator',
    description: 'Compute DAG order and highlight bottleneck chains for high-velocity teams.',
    status: 'TODO',
    priority: 'MEDIUM',
    assignee: 'felixsu',
    createdAt: Date.now() - 3600000 * 6,
    updatedAt: Date.now() - 3600000 * 1,
    dependencies: ['TSK-102'],
    complexity: 'M',
    acceptanceCriteria: ['Cycle detection in graph', 'Critical path calculation'],
  },
  {
    id: 'TSK-105',
    title: 'Capacitor mobile touch ergonomics & swipe-to-action gestures',
    description: 'Enforce 44px touch targets, swipe-to-done, and thumb zone navigation.',
    status: 'BLOCKED',
    blockingReason: 'Waiting for touch hit target audit in mobile viewport',
    priority: 'HIGH',
    assignee: 'felixsu',
    createdAt: Date.now() - 3600000 * 5,
    updatedAt: Date.now() - 3600000 * 1,
    dependencies: ['TSK-102'],
    complexity: 'M',
    acceptanceCriteria: ['Swipe right marks DONE', 'Swipe left reveals actions', 'Safe area padding on iOS/Android'],
  },
];

const STATUS_CYCLE: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];

class TaskStore {
  // Svelte 5 Runes state
  tasks = $state<Task[]>([]);
  selectedIndex = $state<number>(0);
  editingTaskId = $state<string | null>(null);
  isLoaded = $state<boolean>(false);
  lastLatencyMs = $state<number>(0);
  viewMode = $state<'TABLE' | 'KANBAN'>('TABLE');
  currentUser = $state<UserProfile | null>(null);
  isBackendConnected = $state<boolean>(false);

  // Filters
  filter = $state<TaskFilter>({
    searchQuery: '',
    status: 'ALL',
    priority: 'ALL',
    onlyCriticalPath: false,
  });

  constructor() {
    this.init();
  }

  private async init() {
    try {
      // 1. Check if token exists & verify backend
      if (api.getToken()) {
        try {
          const user = await api.getMe();
          this.currentUser = user;
          await this.syncWithBackend();
          this.isBackendConnected = true;
          this.isLoaded = true;
          return;
        } catch (e) {
          console.warn('Backend authentication failed or offline, loading local IndexedDB fallback:', e);
        }
      }

      // 2. Load from IndexedDB
      const stored = await get<Task[]>(DB_KEY);
      if (stored && Array.isArray(stored) && stored.length > 0) {
        this.tasks = stored;
      } else {
        this.tasks = INITIAL_TASKS;
        await set(DB_KEY, INITIAL_TASKS);
      }
    } catch (err) {
      console.error('Failed to initialize taskStore:', err);
      this.tasks = INITIAL_TASKS;
    } finally {
      this.isLoaded = true;
    }
  }

  async syncWithBackend(projectId: number = 1) {
    try {
      const backendTasks = await api.getTasks(projectId);
      if (backendTasks && Array.isArray(backendTasks)) {
        const mapped: Task[] = backendTasks.map((t) => ({
          id: `TSK-${t.id}`,
          title: t.title,
          description: t.description || '',
          status: t.status as TaskStatus,
          priority: t.priority as TaskPriority,
          complexity: t.complexity_points === 1 ? 'S' : t.complexity_points === 2 ? 'M' : t.complexity_points === 3 ? 'L' : 'XL',
          dueDate: t.due_date,
          blockingReason: t.blocking_reason,
          dependencies: t.dependencies || [],
          acceptanceCriteria: t.acceptance_criteria || [],
          createdAt: new Date(t.created_at).getTime(),
          updatedAt: new Date(t.updated_at).getTime(),
        }));
        this.tasks = mapped;
        this.isBackendConnected = true;
        await this.persist();
      }
    } catch (e) {
      console.warn('Backend sync unavailable:', e);
      this.isBackendConnected = false;
    }
  }

  private async persist() {
    const t0 = performance.now();
    try {
      await set(DB_KEY, $state.snapshot(this.tasks));
      this.lastLatencyMs = Math.round((performance.now() - t0) * 10) / 10;
    } catch (err) {
      console.error('Persistence failure:', err);
    }
  }

  // Reactive Derived States
  filteredTasks = $derived.by(() => {
    let result = this.tasks;

    if (this.filter.searchQuery.trim()) {
      const q = this.filter.searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.id.toLowerCase().includes(q) ||
          (t.description && t.description.toLowerCase().includes(q))
      );
    }

    if (this.filter.status !== 'ALL') {
      result = result.filter((t) => t.status === this.filter.status);
    }

    if (this.filter.priority !== 'ALL') {
      result = result.filter((t) => t.priority === this.filter.priority);
    }

    if (this.filter.onlyCriticalPath) {
      const critSet = this.criticalPathIds;
      result = result.filter((t) => critSet.has(t.id));
    }

    return result;
  });

  selectedTask = $derived.by(() => {
    const list = this.filteredTasks;
    if (list.length === 0) return null;
    const clampedIndex = Math.max(0, Math.min(this.selectedIndex, list.length - 1));
    return list[clampedIndex] || null;
  });

  criticalPathIds = $derived.by(() => {
    return computeCriticalPath(this.tasks);
  });

  dagOrder = $derived.by(() => {
    return topologicalSort(this.tasks);
  });

  metrics = $derived.by(() => {
    const total = this.tasks.length;
    const done = this.tasks.filter((t) => t.status === 'DONE').length;
    const inProgress = this.tasks.filter((t) => t.status === 'IN_PROGRESS').length;
    const blocked = this.tasks.filter((t) => t.status === 'BLOCKED').length;
    const todo = this.tasks.filter((t) => t.status === 'TODO').length;
    const rate = total > 0 ? Math.round((done / total) * 100) : 0;

    return { total, done, inProgress, blocked, todo, rate };
  });

  // Action Methods
  selectTask(index: number) {
    const maxIdx = this.filteredTasks.length - 1;
    this.selectedIndex = Math.max(0, Math.min(index, maxIdx));
  }

  selectNext() {
    this.selectTask(this.selectedIndex + 1);
  }

  selectPrev() {
    this.selectTask(this.selectedIndex - 1);
  }

  createTask(title: string, priority: TaskPriority = 'MEDIUM', status: TaskStatus = 'TODO'): Task | null {
    if (!title.trim()) return null;
    const nextNum = this.tasks.length > 0
      ? Math.max(...this.tasks.map((t) => parseInt(t.id.replace(/\D/g, ''), 10) || 100)) + 1
      : 101;
    const id = `TSK-${nextNum}`;
    const now = Date.now();

    const newTask: Task = {
      id,
      title: title.trim(),
      status,
      priority,
      complexity: 'M',
      createdAt: now,
      updatedAt: now,
      dependencies: [],
      acceptanceCriteria: [],
    };

    this.tasks = [newTask, ...this.tasks];
    this.persist();

    // Background sync to backend if connected
    if (this.isBackendConnected) {
      api.createTask({
        project_id: 1,
        title: newTask.title,
        status: newTask.status,
        priority: newTask.priority,
        complexity_points: 2,
      }).catch((e) => console.warn('Failed background API task creation:', e));
    }

    return newTask;
  }

  updateTask(id: string, updates: Partial<Omit<Task, 'id' | 'createdAt'>>) {
    this.tasks = this.tasks.map((t) => {
      if (t.id === id) {
        return { ...t, ...updates, updatedAt: Date.now() };
      }
      return t;
    });
    this.persist();

    // Sync to backend if numeric ID
    const numId = parseInt(id.replace(/\D/g, ''), 10);
    if (this.isBackendConnected && !isNaN(numId)) {
      api.updateTask(numId, updates).catch(() => {});
    }
  }

  deleteTask(id: string) {
    this.tasks = this.tasks.filter((t) => t.id !== id);
    this.tasks = this.tasks.map((t) => {
      if (t.dependencies && t.dependencies.includes(id)) {
        return { ...t, dependencies: t.dependencies.filter((d) => d !== id) };
      }
      return t;
    });
    this.persist();

    const numId = parseInt(id.replace(/\D/g, ''), 10);
    if (this.isBackendConnected && !isNaN(numId)) {
      api.deleteTask(numId).catch(() => {});
    }
  }

  setStatus(id: string, status: TaskStatus) {
    this.updateTask(id, { status });
  }

  cycleStatus(id: string) {
    const task = this.tasks.find((t) => t.id === id);
    if (!task) return;
    const currentIdx = STATUS_CYCLE.indexOf(task.status);
    const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length];
    this.setStatus(id, nextStatus);
  }

  cycleSelectedStatus() {
    const t = this.selectedTask;
    if (t) this.cycleStatus(t.id);
  }

  setPriority(id: string, priority: TaskPriority) {
    this.updateTask(id, { priority });
  }

  startEditing(id: string) {
    this.editingTaskId = id;
  }

  stopEditing() {
    this.editingTaskId = null;
  }

  setFilterStatus(status: FilterStatus) {
    this.filter.status = status;
    this.selectedIndex = 0;
  }

  setFilterPriority(priority: FilterPriority) {
    this.filter.priority = priority;
    this.selectedIndex = 0;
  }

  setSearchQuery(query: string) {
    this.filter.searchQuery = query;
    this.selectedIndex = 0;
  }

  toggleCriticalPathOnly() {
    this.filter.onlyCriticalPath = !this.filter.onlyCriticalPath;
    this.selectedIndex = 0;
  }

  toggleViewMode() {
    this.viewMode = this.viewMode === 'TABLE' ? 'KANBAN' : 'TABLE';
  }

  exportJSON(): string {
    return JSON.stringify(this.tasks, null, 2);
  }

  importJSON(jsonString: string): { success: boolean; count?: number; error?: string } {
    try {
      const parsed = JSON.parse(jsonString);
      if (!Array.isArray(parsed)) {
        return { success: false, error: 'Expected an array of tasks.' };
      }
      this.tasks = parsed;
      this.persist();
      return { success: true, count: parsed.length };
    } catch (e: any) {
      return { success: false, error: e.message || 'Invalid JSON format.' };
    }
  }

  async resetToDefault() {
    this.tasks = INITIAL_TASKS;
    await this.persist();
  }
}

export const taskStore = new TaskStore();
