/**
 * Koshi Frontend API Client
 * Connects Vue 3 frontend with FastAPI backend using JWT Bearer authentication.
 */

const API_BASE = '/api';

/**
 * A user account. Note there is no `role` field: roles are per-project and
 * live on ProjectMember, reachable via `my_role` on a Project.
 */
export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  skills: string;
  avatar_url?: string | null;
}

export type ProjectRole = 'PM' | 'MEMBER';

/**
 * The server's canonical task id is an integer; the UI shows "TSK-n".
 * These two helpers are the only place that translation is allowed to happen —
 * scattering it was how the two representations drifted apart (F-01).
 */
export const taskKeyOf = (serverId: number): string => `TSK-${serverId}`;

export function serverIdOf(key: string): number | null {
  const parsed = Number.parseInt(String(key).replace(/^TSK-/i, ''), 10);
  return Number.isNaN(parsed) ? null : parsed;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  owner_id: number | null;
  created_at: string;
  /** The calling user's role in this project. */
  my_role: ProjectRole | null;
  member_count: number;
}

export interface ProjectMember {
  user_id: number;
  project_id: number;
  role: ProjectRole;
  full_name: string;
  email: string;
  skills: string;
  avatar_url?: string | null;
  active_tasks_count: number;
  wip_points: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('koshi_jwt_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('koshi_jwt_token', token);
      } else {
        localStorage.removeItem('koshi_jwt_token');
      }
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');

    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errBody.detail || `HTTP Error ${res.status}`);
    }

    if (res.status === 204) {
      return null as T;
    }

    return res.json();
  }

  // Auth Endpoints
  /**
   * Create an account. No role is sent or accepted — a new account has no
   * authority anywhere until it creates a project or is invited to one.
   */
  async register(email: string, password: string, full_name: string, skills?: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, skills }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>('/auth/me');
  }

  logout() {
    this.setToken(null);
  }

  /** Self-service profile edit. Roles are not settable here — they are per-project. */
  async updateProfile(userId: number, changes: { full_name?: string; skills?: string }): Promise<UserProfile> {
    return this.request<UserProfile>(`/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(changes),
    });
  }

  // Project Endpoints (personal dashboard)
  async listProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects');
  }

  async createProject(name: string, description = ''): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  }

  async getProject(projectId: number): Promise<Project> {
    return this.request<Project>(`/projects/${projectId}`);
  }

  async deleteProject(projectId: number): Promise<void> {
    return this.request<void>(`/projects/${projectId}`, { method: 'DELETE' });
  }

  // Per-project role management (PM only, enforced server-side)
  async listMembers(projectId: number): Promise<ProjectMember[]> {
    return this.request<ProjectMember[]>(`/projects/${projectId}/members`);
  }

  async addMember(projectId: number, email: string, role: ProjectRole = 'MEMBER'): Promise<ProjectMember> {
    return this.request<ProjectMember>(`/projects/${projectId}/members`, {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    });
  }

  async updateMemberRole(projectId: number, userId: number, role: ProjectRole): Promise<ProjectMember> {
    return this.request<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  }

  async removeMember(projectId: number, userId: number): Promise<void> {
    return this.request<void>(`/projects/${projectId}/members/${userId}`, { method: 'DELETE' });
  }

  // Task Endpoints
  async getTasks(projectId: number): Promise<any[]> {
    return this.request<any[]>(`/tasks?project_id=${projectId}`);
  }

  async createTask(taskData: any): Promise<any> {
    return this.request<any>('/tasks', {
      method: 'POST',
      body: JSON.stringify(taskData),
    });
  }

  async updateTask(taskId: number, taskData: any): Promise<any> {
    return this.request<any>(`/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(taskData),
    });
  }

  async deleteTask(taskId: number): Promise<void> {
    return this.request<void>(`/tasks/${taskId}`, {
      method: 'DELETE',
    });
  }

  async cycleTaskStatus(taskId: number): Promise<any> {
    return this.request<any>(`/tasks/${taskId}/cycle-status`, {
      method: 'POST',
    });
  }

  // AI Workflows & Analysis
  async getWeeklySummary(projectId: number): Promise<{ status: string; summary: string }> {
    return this.request<{ status: string; summary: string }>(`/ai/weekly-summary?project_id=${projectId}`, {
      method: 'POST',
    });
  }

  async extractMeetingMinutes(notes: string): Promise<any> {
    return this.request<any>('/ai/meeting-minutes', {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async recommendAssignment(title: string, description: string, projectId: number): Promise<any> {
    return this.request<any>(`/ai/recommend-assignment?project_id=${projectId}`, {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    });
  }

  async decomposeGoal(goal: string): Promise<any> {
    return this.request<any>('/ai/decompose', {
      method: 'POST',
      body: JSON.stringify({ goal }),
    });
  }

  // NOTE: Git diff analysis is deliberately NOT here. It is a pure client-side
  // function, `lib/gitParser.ts::parseGitDiff`, called directly by GitDiffModal.
  // A stub used to live at this spot and shadowed the real parser, returning
  // fabricated results that did not even satisfy GitDiffAnalysisResult (F-25).

  // Workload & Delayed Tasks
  async getWorkloads(projectId: number): Promise<any[]> {
    return this.request<any[]>(`/stats/workload?project_id=${projectId}`);
  }

  async getDelayedTasks(projectId: number): Promise<any[]> {
    return this.request<any[]>(`/stats/delayed-tasks?project_id=${projectId}`);
  }
}

export const api = new ApiClient();
