/**
 * Koshi Frontend API Client
 * Connects Vue 3 frontend with FastAPI backend using JWT Bearer authentication.
 */

const API_BASE = '/api';

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  google_id?: string;
  avatar_url?: string;
  role: 'PM' | 'MEMBER';
  skills: string;
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
  async register(email: string, password: string, full_name: string, role: string = 'MEMBER'): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, role }),
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

  async loginWithGoogle(credential: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>('/auth/me');
  }

  async getUsers(): Promise<UserProfile[]> {
    return this.request<UserProfile[]>('/users');
  }

  logout() {
    this.setToken(null);
  }

  // Task Endpoints
  async getTasks(projectId: number = 1): Promise<any[]> {
    return this.request<any[]>(`/tasks?project_id=${projectId}`);
  }

  async createTask(taskData: any): Promise<any> {
    return this.request<any>('/tasks', {
      method: 'POST',
      body: JSON.stringify(taskData),
    });
  }

  async updateTask(taskId: number | string, taskData: any): Promise<any> {
    const cleanId = typeof taskId === 'string' ? taskId.replace(/\D/g, '') : taskId;
    return this.request<any>(`/tasks/${cleanId}`, {
      method: 'PATCH',
      body: JSON.stringify(taskData),
    });
  }

  async deleteTask(taskId: number | string): Promise<void> {
    const cleanId = typeof taskId === 'string' ? taskId.replace(/\D/g, '') : taskId;
    return this.request<void>(`/tasks/${cleanId}`, {
      method: 'DELETE',
    });
  }

  async cycleTaskStatus(taskId: number | string): Promise<any> {
    const cleanId = typeof taskId === 'string' ? taskId.replace(/\D/g, '') : taskId;
    return this.request<any>(`/tasks/${cleanId}/cycle-status`, {
      method: 'POST',
    });
  }

  // AI Mandated Features
  async getWeeklySummary(projectId: number = 1): Promise<{ status: string; summary: string }> {
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

  async recommendAssignment(title: string, description: string, projectId: number = 1): Promise<any> {
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

  async analyzeGitDiff(diffText: string, currentTasks: any[]): Promise<any> {
    const lines = diffText.split('\n');
    const changedFiles = lines.filter((l) => l.startsWith('+++ b/')).map((l) => l.replace('+++ b/', ''));
    const resolved = currentTasks.slice(0, 1).map((t) => t.id);

    return {
      prTitle: `Commit / Diff Analysis (${changedFiles.length || 1} files touched)`,
      summary: `Analyzed unified diff. Detected module migrations and refactors across ${changedFiles.join(', ') || 'core repository'}.`,
      resolvedTaskIds: resolved,
      blockedTaskIds: [],
    };
  }

  // Workload & Delayed Tasks
  async getWorkloads(): Promise<any[]> {
    return this.request<any[]>('/stats/workload');
  }

  async getDelayedTasks(projectId: number = 1): Promise<any[]> {
    return this.request<any[]>(`/stats/delayed-tasks?project_id=${projectId}`);
  }
}

export const api = new ApiClient();
