import { get, set } from 'idb-keyval';
import type { Task, TaskStatus, TaskPriority, TaskFilter, FilterStatus, FilterPriority } from '../types/task';
import { topologicalSort, computeCriticalPath } from '../lib/dagSorter';

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
      const stored = await get<Task[]>(DB_KEY);
      if (stored && Array.isArray(stored) && stored.length > 0) {
        this.tasks = stored;
      } else {
        const local = localStorage.getItem(DB_KEY);
        if (local) {
          this.tasks = JSON.parse(local);
        } else {
          this.tasks = INITIAL_TASKS;
        }
      }
    } catch {
      const local = localStorage.getItem(DB_KEY);
      this.tasks = local ? JSON.parse(local) : INITIAL_TASKS;
    } finally {
      this.isLoaded = true;
      this.clampSelection();
    }
  }

  private persist() {
    const data = $state.snapshot(this.tasks);
    try {
      localStorage.setItem(DB_KEY, JSON.stringify(data));
      set(DB_KEY, data).catch((err) => console.error('IndexedDB write error', err));
    } catch (e) {
      console.warn('Storage sync warning', e);
    }
  }

  private measureLatency(fn: () => void) {
    const t0 = performance.now();
    fn();
    const t1 = performance.now();
    this.lastLatencyMs = Math.round((t1 - t0) * 100) / 100;
  }

  // Derived filtered & ordered tasks
  filteredTasks = $derived.by(() => {
    let result = this.tasks;

    // Filter by search query
    if (this.filter.searchQuery.trim()) {
      const q = this.filter.searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.id.toLowerCase().includes(q) ||
          (t.description && t.description.toLowerCase().includes(q)) ||
          (t.assignee && t.assignee.toLowerCase().includes(q))
      );
    }

    // Filter by status
    if (this.filter.status !== 'ALL') {
      result = result.filter((t) => t.status === this.filter.status);
    }

    // Filter by priority
    if (this.filter.priority !== 'ALL') {
      result = result.filter((t) => t.priority === this.filter.priority);
    }

    // Filter by critical path
    if (this.filter.onlyCriticalPath) {
      const cpSet = computeCriticalPath(this.tasks);
      result = result.filter((t) => cpSet.has(t.id));
    }

    return result;
  });

  // Topologically sorted list
  topoSortedTasks = $derived.by(() => {
    return topologicalSort(this.tasks);
  });

  // Critical path set
  criticalPathIds = $derived.by(() => {
    return computeCriticalPath(this.tasks);
  });

  // Summary Metrics
  metrics = $derived.by(() => {
    const total = this.tasks.length;
    const done = this.tasks.filter((t) => t.status === 'DONE').length;
    const inProgress = this.tasks.filter((t) => t.status === 'IN_PROGRESS').length;
    const blocked = this.tasks.filter((t) => t.status === 'BLOCKED').length;
    const critical = this.tasks.filter((t) => t.priority === 'CRITICAL' && t.status !== 'DONE').length;
    const completionRate = total > 0 ? Math.round((done / total) * 100) : 0;

    return { total, done, inProgress, blocked, critical, completionRate };
  });

  // Active selected task
  selectedTask = $derived.by(() => {
    const list = this.filteredTasks;
    if (list.length === 0) return null;
    const idx = Math.min(Math.max(0, this.selectedIndex), list.length - 1);
    return list[idx] || null;
  });

  // Actions
  clampSelection() {
    const len = this.filteredTasks.length;
    if (len === 0) {
      this.selectedIndex = 0;
    } else if (this.selectedIndex >= len) {
      this.selectedIndex = len - 1;
    } else if (this.selectedIndex < 0) {
      this.selectedIndex = 0;
    }
  }

  selectNext() {
    const maxIdx = this.filteredTasks.length - 1;
    if (maxIdx <= 0) return;
    this.selectedIndex = Math.min(this.selectedIndex + 1, maxIdx);
  }

  selectPrev() {
    if (this.selectedIndex <= 0) return;
    this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
  }

  selectIndex(idx: number) {
    const maxIdx = this.filteredTasks.length - 1;
    this.selectedIndex = Math.max(0, Math.min(idx, maxIdx));
  }

  cycleSelectedStatus() {
    const current = this.selectedTask;
    if (!current) return;
    this.cycleStatus(current.id);
  }

  cycleStatus(taskId: string) {
    this.measureLatency(() => {
      const idx = this.tasks.findIndex((t) => t.id === taskId);
      if (idx === -1) return;

      const currentStatus = this.tasks[idx].status;
      const nextIdx = (STATUS_CYCLE.indexOf(currentStatus) + 1) % STATUS_CYCLE.length;
      const nextStatus = STATUS_CYCLE[nextIdx];

      this.tasks[idx] = {
        ...this.tasks[idx],
        status: nextStatus,
        blockingReason: nextStatus === 'BLOCKED' ? (this.tasks[idx].blockingReason || 'Blocked by upstream dependency') : undefined,
        updatedAt: Date.now(),
      };
      this.persist();
    });
  }

  setStatus(taskId: string, status: TaskStatus, blockingReason?: string) {
    this.measureLatency(() => {
      const idx = this.tasks.findIndex((t) => t.id === taskId);
      if (idx === -1) return;
      this.tasks[idx] = {
        ...this.tasks[idx],
        status,
        blockingReason: status === 'BLOCKED' ? (blockingReason || this.tasks[idx].blockingReason || 'Action required') : undefined,
        updatedAt: Date.now(),
      };
      this.persist();
    });
  }

  setPriority(taskId: string, priority: TaskPriority) {
    this.measureLatency(() => {
      const idx = this.tasks.findIndex((t) => t.id === taskId);
      if (idx === -1) return;
      this.tasks[idx] = {
        ...this.tasks[idx],
        priority,
        updatedAt: Date.now(),
      };
      this.persist();
    });
  }

  updateTaskTitle(taskId: string, newTitle: string) {
    if (!newTitle.trim()) return;
    this.measureLatency(() => {
      const idx = this.tasks.findIndex((t) => t.id === taskId);
      if (idx === -1) return;
      this.tasks[idx] = {
        ...this.tasks[idx],
        title: newTitle.trim(),
        updatedAt: Date.now(),
      };
      this.editingTaskId = null;
      this.persist();
    });
  }

  startEditing(taskId: string) {
    this.editingTaskId = taskId;
  }

  stopEditing() {
    this.editingTaskId = null;
  }

  createTask(title: string, priority: TaskPriority = 'MEDIUM', status: TaskStatus = 'TODO') {
    if (!title.trim()) return null;
    let created: Task | null = null;
    this.measureLatency(() => {
      const nextNum = this.tasks.length + 101;
      const id = `TSK-${nextNum}`;
      const newTask: Task = {
        id,
        title: title.trim(),
        status,
        priority,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        complexity: 'M',
      };
      this.tasks = [newTask, ...this.tasks];
      this.selectedIndex = 0;
      this.persist();
      created = newTask;
    });
    return created;
  }

  addBatchTasks(newTasks: Task[]) {
    this.measureLatency(() => {
      this.tasks = [...newTasks, ...this.tasks];
      this.persist();
    });
  }

  deleteTask(taskId: string) {
    this.measureLatency(() => {
      this.tasks = this.tasks.filter((t) => t.id !== taskId);
      this.clampSelection();
      this.persist();
    });
  }

  deleteSelected() {
    const current = this.selectedTask;
    if (!current) return;
    this.deleteTask(current.id);
  }

  setFilterStatus(status: FilterStatus) {
    this.filter.status = status;
    this.selectedIndex = 0;
  }

  setFilterPriority(priority: FilterPriority) {
    this.filter.priority = priority;
    this.selectedIndex = 0;
  }

  setSearchQuery(q: string) {
    this.filter.searchQuery = q;
    this.selectedIndex = 0;
  }

  toggleCriticalPathOnly() {
    this.filter.onlyCriticalPath = !this.filter.onlyCriticalPath;
    this.selectedIndex = 0;
  }

  // Export / Import
  exportJSON(): string {
    const data = {
      project: 'Koshi',
      version: '1.0.0',
      exportedAt: new Date().toISOString(),
      tasks: $state.snapshot(this.tasks),
    };
    return JSON.stringify(data, null, 2);
  }

  importJSON(jsonString: string): { success: boolean; count: number; error?: string } {
    try {
      const parsed = JSON.parse(jsonString);
      let items: Task[] = [];
      if (Array.isArray(parsed)) {
        items = parsed;
      } else if (parsed && Array.isArray(parsed.tasks)) {
        items = parsed.tasks;
      } else {
        throw new Error('Invalid JSON format: expected Task array or { tasks: Task[] }');
      }

      // Basic validation
      const validTasks: Task[] = items.map((t, idx) => ({
        id: t.id || `TSK-${100 + idx}`,
        title: t.title || 'Untitled Task',
        description: t.description || '',
        status: ['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'].includes(t.status) ? t.status : 'TODO',
        priority: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(t.priority) ? t.priority : 'MEDIUM',
        assignee: t.assignee,
        dueDate: t.dueDate,
        blockingReason: t.blockingReason,
        createdAt: t.createdAt || Date.now(),
        updatedAt: t.updatedAt || Date.now(),
        dependencies: Array.isArray(t.dependencies) ? t.dependencies : [],
        complexity: t.complexity,
        acceptanceCriteria: Array.isArray(t.acceptanceCriteria) ? t.acceptanceCriteria : [],
      }));

      this.tasks = validTasks;
      this.persist();
      this.selectedIndex = 0;
      return { success: true, count: validTasks.length };
    } catch (e: any) {
      return { success: false, count: 0, error: e.message };
    }
  }

  resetToDefault() {
    this.tasks = INITIAL_TASKS;
    this.persist();
    this.selectedIndex = 0;
  }
}

export const taskStore = new TaskStore();
