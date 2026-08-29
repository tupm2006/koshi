import { defineStore } from 'pinia';
import { nextTick } from 'vue';
import { get, set } from 'idb-keyval';
import type { Task, TaskAssignee, TaskStatus, TaskPriority, TaskFilter, FilterStatus, FilterPriority, Complexity } from '../types/task';
import { topologicalSort, computeCriticalPath } from '../lib/dagSorter';
import { sortByUrgency } from '../lib/urgency';
import { api, taskKeyOf, serverIdOf, type UserProfile, type Project, type ProjectRole, type Invitation, type ProjectMember, type AppNotification } from '../services/api';

/**
 * IndexedDB keys are partitioned per project.
 *
 * A single shared key was safe while Koshi was single-project, but with the
 * per-project model it would let the cache of one project be read back as
 * another's — and an offline edit could then be synced to the wrong project.
 * The `v2` generation marks the layout change; `v1` values are simply ignored.
 */
const tasksKey = (projectId: number) => `koshi_tasks_v2_p${projectId}`;

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
    // Personal dashboard state. Roles are per-project, so `myRole` is a property
    // of the *selected* project, never of the user.
    projects: [] as Project[],
    currentProjectId: null as number | null,
    isDashboardOpen: false,
    /**
     * Which top-level screen is showing.
     *
     * LANDING is what an unauthenticated visitor gets; BOARD is the working
     * app; PROFILE is the account page. A tiny state machine rather than a
     * router — there are three screens and no URLs to preserve, so a dependency
     * would buy nothing.
     */
    appView: 'LANDING' as 'LANDING' | 'BOARD' | 'PROFILE' | 'NOTIFICATIONS',
    /** The feed, newest first. Loaded on demand and after posting. */
    notifications: [] as AppNotification[],
    /** Kept separately from `notifications.length` so the badge is correct
     *  before the feed has ever been opened. */
    unreadCount: 0,
    filter: {
      searchQuery: '',
      status: 'ALL',
      priority: 'ALL',
      onlyCriticalPath: false,
    } as TaskFilter,
    /**
     * Whose tasks the board shows: everyone, me, or one named person.
     *
     * A PM opens on ALL because their job is the whole project; a member opens
     * on MINE because theirs is their own queue. Either can switch to anybody —
     * this is about attention, not permission, and a member seeing what a
     * teammate is carrying is how they know who to ask.
     */
    scope: 'ALL' as 'ALL' | 'MINE' | number,
    /** Roster of the selected project, for the assignee picker and filter. */
    members: [] as ProjectMember[],
    /**
     * Task awaiting completion evidence, or null.
     *
     * Set when a task enters DONE. The transition itself is never blocked on
     * it — the work is finished whether or not proof gets attached, and a
     * dialog that could strand a task in IN_PROGRESS because a network call
     * failed would be worse than no dialog.
     */
    evidenceForTaskId: null as string | null,
    /** Pending project invitations awaiting this user's answer. */
    invitations: [] as Invitation[],
  }),

  getters: {
    currentProject(state): Project | null {
      return state.projects.find((p) => p.id === state.currentProjectId) || null;
    },

    /** The caller's role in the *selected* project, not a global role. */
    myRole(): ProjectRole | null {
      return (this as any).currentProject?.my_role ?? null;
    },

    /** Whether the UI should offer PM-only affordances for the selected project. */
    isProjectManager(): boolean {
      return (this as any).myRole === 'PM';
    },

    /**
     * A project with exactly one member — nobody else can be editing it.
     */
    isPersonalProject(): boolean {
      return ((this as any).currentProject?.member_count ?? 0) <= 1;
    },

    /**
     * Whether local edits are allowed right now.
     *
     * Offline editing is safe on a personal project: there is no second writer,
     * so last-write-wins cannot lose anyone else's work. On a shared project it
     * is not — two members editing the same task offline would silently
     * overwrite each other on reconnect, and there is no reconciliation
     * (RISK-13). Shared projects therefore go read-only while disconnected.
     */
    canMutate(): boolean {
      if ((this as any).currentProjectId === null) return false;
      if ((this as any).isBackendConnected) return true;
      return (this as any).isPersonalProject;
    },

    isReadOnly(): boolean {
      return !(this as any).canMutate;
    },

    /** Why editing is blocked, for display. Null when editing is allowed. */
    readOnlyReason(): string | null {
      if ((this as any).canMutate) return null;
      if ((this as any).currentProjectId === null) return 'NO_PROJECT';
      return 'OFFLINE_SHARED';
    },

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

      // ALL means no filter. MINE resolves to the signed-in user; a number is
      // a specific person. Resolving MINE here rather than storing the id keeps
      // the filter correct if the session changes underneath it.
      const wantedId =
        state.scope === 'ALL' ? null
        : state.scope === 'MINE' ? (state.currentUser?.id ?? null)
        : state.scope;

      if (wantedId !== null) {
        result = result.filter((t) => (t.assignees ?? []).some((a) => a.id === wantedId));
      }

      // Deadline-first ordering (see lib/urgency.ts). `Date.now()` is read here
      // rather than inside the sorter so the sorter stays testable.
      return sortByUrgency(result, Date.now());
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
    /**
     * Single entry point for "a user just became authenticated".
     *
     * Login, registration and boot all funnel through here so the post-auth
     * sequence cannot drift between them — that drift was exactly the bug where
     * signing in left the board empty with no projects loaded.
     */
    async onAuthenticated(user: UserProfile) {
      this.currentUser = user;
      this.isBackendConnected = true;
      this.appView = 'BOARD';

      const projects = await this.loadProjects();
      await this.loadInvitations();
      await this.refreshUnreadCount();
      if (this.currentProjectId !== null) {
        await this.selectProject(this.currentProjectId);
      } else {
        // Brand-new account: nothing to show on the board, so send them
        // straight to the dashboard to create their first project.
        this.tasks = [];
        this.isDashboardOpen = true;
      }
      return projects;
    },

    /**
     * Fetch pending invitations. Never throws: a failure here must not stop the
     * board from loading — an invitation is a nicety, the board is the product.
     */
    async loadNotifications(unreadOnly = false) {
      if (!this.isBackendConnected) return;
      try {
        this.notifications = await api.listNotifications(unreadOnly);
        this.unreadCount = this.notifications.filter((n) => n.read_at === null).length;
      } catch (e) {
        console.warn('Could not load notifications:', e);
      }
    },

    /** Just the badge. Cheap enough to call on every sign-in. */
    async refreshUnreadCount() {
      if (!this.isBackendConnected) return;
      try {
        this.unreadCount = await api.unreadNotificationCount();
      } catch (e) {
        console.warn('Could not load the unread count:', e);
      }
    },

    async markNotificationRead(id: number) {
      const n = this.notifications.find((x) => x.id === id);
      if (!n || n.read_at !== null) return;
      // Optimistic: the badge should drop the moment it is clicked. The server
      // call is idempotent, so a failure leaves it merely out of date until the
      // next load rather than wrong in a way that compounds.
      n.read_at = new Date().toISOString();
      this.unreadCount = Math.max(0, this.unreadCount - 1);
      try {
        await api.markNotificationRead(id);
      } catch (e) {
        console.warn('Could not mark as read:', e);
      }
    },

    async markAllNotificationsRead() {
      const now = new Date().toISOString();
      this.notifications.forEach((n) => { if (n.read_at === null) n.read_at = now; });
      this.unreadCount = 0;
      try {
        await api.markAllNotificationsRead();
      } catch (e) {
        console.warn('Could not mark all as read:', e);
      }
    },

    showNotifications() {
      this.appView = 'NOTIFICATIONS';
      this.loadNotifications();
    },

    /**
     * Open the task a notification points at.
     *
     * Switching project first, because the task may well be in a different one
     * — that is precisely when a notification is most useful.
     */
    async openNotification(n: AppNotification) {
      await this.markNotificationRead(n.id);
      if (n.project_id !== null && n.project_id !== this.currentProjectId) {
        await this.selectProject(n.project_id);
      }
      this.appView = 'BOARD';
      if (n.task_id !== null) {
        const key = taskKeyOf(n.task_id);
        const idx = this.filteredTasks.findIndex((t) => t.id === key);
        if (idx >= 0) this.selectedIndex = idx;
        return key;
      }
      return null;
    },

    async loadInvitations() {
      if (!this.isBackendConnected) return;
      try {
        this.invitations = await api.listInvitations();
      } catch (e) {
        console.warn('Could not load invitations:', e);
      }
    },

    async acceptInvitation(projectId: number) {
      const project = await api.acceptInvitation(projectId);
      this.invitations = this.invitations.filter((i) => i.project_id !== projectId);
      // Re-list rather than pushing the returned project: loadProjects is the
      // single path that shapes the dashboard, and duplicating it here is how
      // the two drift (F-21).
      await this.loadProjects();
      await this.selectProject(project.id);
      this.isDashboardOpen = false;
    },

    async declineInvitation(projectId: number) {
      await api.declineInvitation(projectId);
      this.invitations = this.invitations.filter((i) => i.project_id !== projectId);
    },

    dismissEvidencePrompt() {
      this.evidenceForTaskId = null;
    },

    setScope(scope: 'ALL' | 'MINE' | number) {
      this.scope = scope;
      this.selectedIndex = 0;
    },

    async logout() {
      api.logout();
      this.currentUser = null;
      this.projects = [];
      this.invitations = [];
      this.notifications = [];
      this.unreadCount = 0;
      this.scope = 'ALL';
      this.currentProjectId = null;
      this.tasks = [];
      this.isDashboardOpen = false;
      this.selectedIndex = 0;
      this.kanbanColIndex = 0;
      this.kanbanRowIndex = 0;
      // Signing out returns to the landing page, not to a board the user can no
      // longer act on.
      this.appView = 'LANDING';
    },

    showProfile() {
      this.appView = 'PROFILE';
    },

    showBoard() {
      this.appView = 'BOARD';
    },

    /** Push edited profile fields to the server and update local state. */
    async updateProfile(changes: { full_name?: string; skills?: string }) {
      if (!this.currentUser) throw new Error('Not signed in');
      const updated = await api.updateProfile(this.currentUser.id, changes);
      this.currentUser = updated;
      return updated;
    },

    /**
     * Replace the signed-in user's picture.
     *
     * The whole user comes back, so `currentUser` is reassigned rather than
     * patched — one shape, from one source, with no chance of the avatar and
     * the rest of the profile disagreeing.
     */
    async uploadAvatar(file: File) {
      if (!this.currentUser) throw new Error('Not signed in');
      this.currentUser = await api.uploadAvatar(file);
      return this.currentUser;
    },

    async removeAvatar() {
      if (!this.currentUser) throw new Error('Not signed in');
      this.currentUser = await api.removeAvatar();
      return this.currentUser;
    },

    async loadProjects() {
      try {
        const projects = await api.listProjects();
        this.projects = projects;
        this.isBackendConnected = true;

        // Keep the current selection if it is still valid, else fall back to
        // the first project, else leave unselected (a brand-new account).
        if (this.currentProjectId === null || !projects.some((p) => p.id === this.currentProjectId)) {
          this.currentProjectId = projects.length > 0 ? projects[0].id : null;
        }
        return projects;
      } catch (e) {
        console.warn('Could not load projects:', e);
        this.isBackendConnected = false;
        return [];
      }
    },

    async selectProject(projectId: number) {
      this.currentProjectId = projectId;
      // A PM's job is the whole project; a member's is their own queue. This is
      // the default view, not a permission — either role can switch.
      this.scope = this.projects.find((p) => p.id === projectId)?.my_role === 'PM'
        ? 'ALL'
        : 'MINE';
      this.selectedIndex = 0;
      this.kanbanColIndex = 0;
      this.kanbanRowIndex = 0;

      // Local-first: show this project's cached board immediately, then refresh
      // from the backend (INV-03 — never block the render on the network).
      const cached = await get<Task[]>(tasksKey(projectId));
      this.tasks = cached && Array.isArray(cached) ? cached : [];

      await this.syncWithBackend(projectId);
      await this.loadMembers(projectId);
    },

    /**
     * Roster for the assignee picker and the "whose tasks" filter.
     *
     * Accepted members only: somebody who was merely invited cannot open the
     * project, so offering them as an assignee would produce work nobody
     * receives (the server refuses it too — DEC-022).
     */
    async loadMembers(projectId: number) {
      if (!this.isBackendConnected) return;
      try {
        const roster = await api.listMembers(projectId);
        this.members = roster.filter((m) => m.status === 'ACCEPTED');
      } catch (e) {
        console.warn('Could not load members:', e);
        this.members = [];
      }
    },

    async createProject(name: string, description = '') {
      const project = await api.createProject(name, description);
      this.projects = [project, ...this.projects];
      await this.selectProject(project.id);
      return project;
    },

    async init() {
      try {
        if (api.getToken()) {
          try {
            const user = await api.getMe();
            await this.onAuthenticated(user);
            this.isLoaded = true;
            return;
          } catch (e) {
            console.warn('Backend offline or expired token, using local storage fallback:', e);
          }
        }

        // No usable session. There is no signed-out board any more, so there is
        // nothing to load — the landing page is the whole screen.
        this.appView = 'LANDING';
        this.tasks = [];
      } catch (err) {
        console.error('Failed to initialize taskStore:', err);
        this.appView = 'LANDING';
        this.tasks = [];
      } finally {
        this.isLoaded = true;
      }
    },

    async syncWithBackend(projectId?: number) {
      const pid = projectId ?? this.currentProjectId;
      if (pid === null || pid === undefined) {
        return;
      }
      try {
        const backendTasks = await api.getTasks(pid);
        if (backendTasks && Array.isArray(backendTasks)) {
          const mapped: Task[] = backendTasks.map((t) => ({
            id: t.key || taskKeyOf(t.id),
            title: t.title,
            description: t.description || '',
            status: t.status as TaskStatus,
            priority: t.priority as TaskPriority,
            complexity: t.complexity_points === 1 ? 'S' : t.complexity_points === 2 ? 'M' : t.complexity_points === 3 ? 'L' : 'XL',
            dueDate: t.due_date,
            assignees: (t.assignees || []).map((a: any) => ({
              id: a.id, full_name: a.full_name, avatar_url: a.avatar_url ?? null,
            })),
            blockingReason: t.blocking_reason,
            // Server sends integer ids; the board works in display keys.
            dependencies: (t.dependencies || []).map((d: number) => taskKeyOf(d)),
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
      if (this.currentProjectId === null) return;
      const key = tasksKey(this.currentProjectId);
      try {
        await set(key, JSON.parse(JSON.stringify(this.tasks)));
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

    createTask(
      title: string,
      priority: TaskPriority = 'MEDIUM',
      status: TaskStatus = 'TODO',
      extra: { dueDate?: string; assignees?: TaskAssignee[] } = {},
    ): Task | null {
      if (!this.canMutate) return null;
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
        // Undefined rather than empty string when absent: `dueDate` is optional
        // in the contract and '' would sort as an unparseable date.
        dueDate: extra.dueDate || undefined,
        // Kept locally too, not just sent. Without it a task you just assigned
        // vanishes from your own "My tasks" view until the next server sync —
        // local-first means the local copy is complete (INV-03).
        assignees: extra.assignees ?? [],
        createdAt: now,
        updatedAt: now,
        dependencies: [],
        acceptanceCriteria: [],
      };

      this.tasks = [newTask, ...this.tasks];
      this.persist();

      if (this.isBackendConnected) {
        api.createTask({
          project_id: this.currentProjectId,
          title: newTask.title,
          status: newTask.status,
          priority: newTask.priority,
          complexity_points: 2,
          due_date: newTask.dueDate ?? null,
          assignee_ids: (extra.assignees ?? []).map((a) => a.id),
        }).catch((e) => console.warn('Background API create failed:', e));
      }

      return newTask;
    },

    updateTask(id: string, updates: Partial<Omit<Task, 'id' | 'createdAt'>>) {
      if (!this.canMutate) return;

      // Every status change funnels through here, so this is the one place that
      // needs to notice a task being completed.
      const before = this.tasks.find((t) => t.id === id);
      const enteringDone =
        updates.status === 'DONE' && !!before && before.status !== 'DONE';
      this.tasks = this.tasks.map((t) => {
        if (t.id === id) {
          return { ...t, ...updates, updatedAt: Date.now() };
        }
        return t;
      });
      this.persist();

      // Ask after the write, not before: the task is DONE either way.
      // Offline there is nowhere to upload to, so do not offer.
      if (enteringDone && this.isBackendConnected) {
        this.evidenceForTaskId = id;
      }

      const numId = serverIdOf(id);
      if (this.isBackendConnected && numId !== null) {
        // Translate any dependency keys back to the server's integer ids.
        const payload: Record<string, unknown> = { ...updates };
        if (Array.isArray(updates.assignees)) {
          // The contract takes ids; the board carries whole people so it can
          // render a name and an avatar without a second lookup.
          payload.assignee_ids = updates.assignees.map((a) => a.id);
          delete payload.assignees;
        }
        if (Array.isArray(updates.dependencies)) {
          payload.dependencies = updates.dependencies
            .map((d) => serverIdOf(d))
            .filter((d): d is number => d !== null);
        }
        api.updateTask(numId, payload).catch(() => {});
      }
    },

    deleteTask(id: string) {
      if (!this.canMutate) return;
      this.tasks = this.tasks.filter((t) => t.id !== id);
      this.tasks = this.tasks.map((t) => {
        if (t.dependencies && t.dependencies.includes(id)) {
          return { ...t, dependencies: t.dependencies.filter((d) => d !== id) };
        }
        return t;
      });
      this.persist();

      const numId = serverIdOf(id);
      if (this.isBackendConnected && numId !== null) {
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
  },
});
