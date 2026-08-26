import { defineStore } from 'pinia';
import { nextTick } from 'vue';
import { get, set } from 'idb-keyval';
import type { Task, TaskStatus, TaskPriority, TaskFilter, FilterStatus, FilterPriority, Complexity } from '../types/task';
import { topologicalSort, computeCriticalPath } from '../lib/dagSorter';
import { api, type UserProfile } from '../services/api';

const DB_KEY = 'koshi_tasks_v1';

const INITIAL_TASKS: Task[] = [
  {
    id: 'TSK-101',
    title: 'Migrate reactive state to Vue 3 Composition API & Pinia',
    description: 'Provide high-velocity reactivity with TypeScript and component modularity.',
    status: 'IN_PROGRESS',
    priority: 'CRITICAL',
    assignee: 'felixsu',
    dueDate: new Date(Date.now() + 86400000 * 2).toISOString(),
    createdAt: Date.now() - 3600000 * 8,
    updatedAt: Date.now() - 3600000 * 2,
    complexity: 'M',
    acceptanceCriteria: ['Pass customer specification audit', '0 runtime memory leaks', 'Full keyboard navigation'],
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
    description: 'Ensure offline execution with background non-blocking persistence.',
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
    title: 'Develop AI Workflow Endpoints (Summary, Minutes, Assignment)',
    description: 'Structured heuristics and LLM endpoints for progress aggregation and meeting extraction.',
    status: 'BLOCKED',
    blockingReason: 'Waiting for upstream Gemini API proxy verification',
    priority: 'HIGH',
    assignee: 'felixsu',
    createdAt: Date.now() - 3600000 * 5,
    updatedAt: Date.now() - 3600000 * 1,
    dependencies: ['TSK-102'],
    complexity: 'M',
    acceptanceCriteria: ['Summary generation', 'Meeting action item extraction', 'Workload heuristic load-balancing'],
  },
  {
    id: 'TSK-106',
    title: 'Integrate Vue 3 Composition API with JWT Bearer Token API sync',
    description: 'Ensure authorization headers and silent token refreshes across local-first mutations.',
    status: 'TODO',
    priority: 'HIGH',
    assignee: 'felixsu',
    createdAt: Date.now() - 3600000 * 4,
    updatedAt: Date.now() - 3600000 * 1,
    dependencies: ['TSK-101'],
    complexity: 'M',
    acceptanceCriteria: ['Zero visual auth jitter', 'Local fallback on backend timeout'],
  },
];

const STATUS_ORDER: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];

export const useTaskStore = defineStore('taskStore', {
  state: () => ({
    tasks: [] as Task[],
    selectedIndex: 0,
    kanbanColIndex: 0,
    kanbanRowIndex: 0,
    editingTaskId: null as string | null,
    activeDetailTaskId: null as string | null,
    isLoaded: false,
    lastLatencyMs: 0,
    viewMode: (typeof window !== 'undefined' && window.innerWidth >= 768 ? 'KANBAN' : 'TABLE') as 'TABLE' | 'KANBAN',
    currentUser: null as UserProfile | null,
    isBackendConnected: false,
    filter: {
      searchQuery: '',
      status: 'ALL',
      priority: 'ALL',
      onlyCriticalPath: false,
    } as TaskFilter,
  }),

  getters: {
    filteredTasks(state): Task[] {
      let result = state.tasks;

      if (state.filter.searchQuery.trim()) {
        const q = state.filter.searchQuery.toLowerCase();
        result = result.filter(
          (t) =>
            t.title.toLowerCase().includes(q) ||
            t.id.toLowerCase().includes(q) ||
            (t.description && t.description.toLowerCase().includes(q))
        );
      }

      if (state.filter.status !== 'ALL') {
        result = result.filter((t) => t.status === state.filter.status);
      }

      if (state.filter.priority !== 'ALL') {
        result = result.filter((t) => t.priority === state.filter.priority);
      }

      if (state.filter.onlyCriticalPath) {
        const critSet = computeCriticalPath(state.tasks);
        result = result.filter((t) => critSet.has(t.id));
      }

      return result;
    },

    tasksByColumn(): Record<TaskStatus, Task[]> {
      const cols: Record<TaskStatus, Task[]> = {
        TODO: [],
        IN_PROGRESS: [],
        BLOCKED: [],
        DONE: [],
      };
      for (const task of this.filteredTasks) {
        if (cols[task.status]) {
          cols[task.status].push(task);
        }
      }
      return cols;
    },

    currentColumnTasks(): Task[] {
      const status = STATUS_ORDER[this.kanbanColIndex] || 'TODO';
      return this.tasksByColumn[status] || [];
    },

    activeKanbanTask(): Task | null {
      const tasks = this.currentColumnTasks;
      if (tasks.length === 0) return null;
      const row = Math.max(0, Math.min(this.kanbanRowIndex, tasks.length - 1));
      return tasks[row] || null;
    },

    selectedTask(): Task | null {
      if (this.viewMode === 'KANBAN') {
        return this.activeKanbanTask;
      }
      const list = this.filteredTasks;
      if (list.length === 0) return null;
      const clamped = Math.max(0, Math.min(this.selectedIndex, list.length - 1));
      return list[clamped] || null;
    },

    activeDetailTask(state): Task | null {
      if (!state.activeDetailTaskId) return null;
      return state.tasks.find((t) => t.id === state.activeDetailTaskId) || null;
    },

    criticalPathIds(state): Set<string> {
      return computeCriticalPath(state.tasks);
    },

    dagOrder(state): Task[] {
      return topologicalSort(state.tasks);
    },

    metrics(state) {
      const total = state.tasks.length;
      const done = state.tasks.filter((t) => t.status === 'DONE').length;
      const inProgress = state.tasks.filter((t) => t.status === 'IN_PROGRESS').length;
      const blocked = state.tasks.filter((t) => t.status === 'BLOCKED').length;
      const todo = state.tasks.filter((t) => t.status === 'TODO').length;
      const rate = total > 0 ? Math.round((done / total) * 100) : 0;

      return { total, done, inProgress, blocked, todo, rate };
    },
  },

  actions: {
    async init() {
      try {
        if (api.getToken()) {
          try {
            const user = await api.getMe();
            this.currentUser = user;
            await this.syncWithBackend();
            this.isBackendConnected = true;
            this.isLoaded = true;
            return;
          } catch (e) {
            console.warn('Backend offline or expired token, using local storage fallback:', e);
          }
        }

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
    },

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
    },

    async persist() {
      const t0 = performance.now();
      try {
        await set(DB_KEY, JSON.parse(JSON.stringify(this.tasks)));
        this.lastLatencyMs = Math.round((performance.now() - t0) * 10) / 10;
      } catch (err) {
        console.error('Persistence failure:', err);
      }
    },

    selectTask(index: number) {
      const maxIdx = this.filteredTasks.length - 1;
      this.selectedIndex = Math.max(0, Math.min(index, maxIdx));
    },

    selectNext() {
      this.selectTask(this.selectedIndex + 1);
    },

    selectPrev() {
      this.selectTask(this.selectedIndex - 1);
    },

    openDetail(id?: string) {
      if (id) {
        this.activeDetailTaskId = id;
      } else if (this.selectedTask) {
        this.activeDetailTaskId = this.selectedTask.id;
      }
    },

    closeDetail() {
      this.activeDetailTaskId = null;
    },

    syncKanbanFocusToTask(taskId: string) {
      const task = this.tasks.find((t) => t.id === taskId);
      if (!task) return;

      const targetColIndex = STATUS_ORDER.indexOf(task.status);
      if (targetColIndex === -1) return;

      this.kanbanColIndex = targetColIndex;

      const colTasks = this.tasksByColumn[task.status] || [];
      const targetRowIndex = colTasks.findIndex((t) => t.id === taskId);

      this.kanbanRowIndex = targetRowIndex !== -1 ? targetRowIndex : 0;
    },

    moveKanbanCursor(direction: 'up' | 'down' | 'left' | 'right') {
      if (direction === 'left') {
        this.kanbanColIndex = (this.kanbanColIndex - 1 + 4) % 4;
        const colLen = this.currentColumnTasks.length;
        if (colLen > 0 && this.kanbanRowIndex >= colLen) {
          this.kanbanRowIndex = colLen - 1;
        }
      } else if (direction === 'right') {
        this.kanbanColIndex = (this.kanbanColIndex + 1) % 4;
        const colLen = this.currentColumnTasks.length;
        if (colLen > 0 && this.kanbanRowIndex >= colLen) {
          this.kanbanRowIndex = colLen - 1;
        }
      } else if (direction === 'up') {
        this.kanbanRowIndex = Math.max(0, this.kanbanRowIndex - 1);
      } else if (direction === 'down') {
        const colLen = this.currentColumnTasks.length;
        if (colLen > 0) {
          this.kanbanRowIndex = Math.min(colLen - 1, this.kanbanRowIndex + 1);
        } else {
          this.kanbanRowIndex = 0;
        }
      }
    },

    shiftActiveKanbanTask(direction: 'left' | 'right') {
      const task = this.activeKanbanTask;
      if (!task) return;
      const currIdx = STATUS_ORDER.indexOf(task.status);
      let nextIdx: number;

      if (direction === 'right') {
        nextIdx = (currIdx + 1) % STATUS_ORDER.length;
      } else {
        nextIdx = (currIdx - 1 + STATUS_ORDER.length) % STATUS_ORDER.length;
      }

      const nextStatus = STATUS_ORDER[nextIdx];
      this.setStatus(task.id, nextStatus);

      nextTick(() => {
        this.syncKanbanFocusToTask(task.id);
      });
    },

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

      if (this.isBackendConnected) {
        api.createTask({
          project_id: 1,
          title: newTask.title,
          status: newTask.status,
          priority: newTask.priority,
          complexity_points: 2,
        }).catch((e) => console.warn('Background API create failed:', e));
      }

      return newTask;
    },

    updateTask(id: string, updates: Partial<Omit<Task, 'id' | 'createdAt'>>) {
      this.tasks = this.tasks.map((t) => {
        if (t.id === id) {
          return { ...t, ...updates, updatedAt: Date.now() };
        }
        return t;
      });
      this.persist();

      const numId = parseInt(id.replace(/\D/g, ''), 10);
      if (this.isBackendConnected && !isNaN(numId)) {
        api.updateTask(numId, updates).catch(() => {});
      }
    },

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
    },

    deleteSelected() {
      const selected = this.selectedTask;
      if (selected) {
        this.deleteTask(selected.id);
      }
    },

    setStatus(id: string, status: TaskStatus) {
      this.updateTask(id, { status });
    },

    cycleStatus(id: string) {
      const task = this.tasks.find((t) => t.id === id);
      if (!task) return;
      const currentIdx = STATUS_ORDER.indexOf(task.status);
      const nextStatus = STATUS_ORDER[(currentIdx + 1) % STATUS_ORDER.length];
      this.setStatus(id, nextStatus);

      nextTick(() => {
        this.syncKanbanFocusToTask(id);
      });
    },

    cycleSelectedStatus() {
      const t = this.selectedTask;
      if (t) this.cycleStatus(t.id);
    },

    setPriority(id: string, priority: TaskPriority) {
      this.updateTask(id, { priority });
    },

    startEditing(id: string) {
      this.editingTaskId = id;
    },

    stopEditing() {
      this.editingTaskId = null;
    },

    setFilterStatus(status: FilterStatus) {
      this.filter.status = status;
      this.selectedIndex = 0;
    },

    setFilterPriority(priority: FilterPriority) {
      this.filter.priority = priority;
      this.selectedIndex = 0;
    },

    setSearchQuery(query: string) {
      this.filter.searchQuery = query;
      this.selectedIndex = 0;
    },

    toggleCriticalPathOnly() {
      this.filter.onlyCriticalPath = !this.filter.onlyCriticalPath;
      this.selectedIndex = 0;
    },

    toggleViewMode() {
      this.viewMode = this.viewMode === 'TABLE' ? 'KANBAN' : 'TABLE';
    },

    exportJSON(): string {
      return JSON.stringify(this.tasks, null, 2);
    },

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
    },

    async resetToDefault() {
      this.tasks = INITIAL_TASKS;
      await this.persist();
    },
  },
});
