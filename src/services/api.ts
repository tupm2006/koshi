/**
 * Koshi Frontend API Client
 * Connects Svelte 5 frontend with FastAPI backend using JWT Bearer authentication.
 */

const API_BASE = '/api';

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
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
  async register(email: string, password: str, full_name: string, role: string = 'MEMBER'): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, role }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: str): Promise<AuthResponse> {
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

  // Workload & Delayed Tasks
  async getWorkloads(): Promise<any[]> {
    return this.request<any[]>('/stats/workload');
  }

  async getDelayedTasks(projectId: number = 1): Promise<any[]> {
    return this.request<any[]>(`/stats/delayed-tasks?project_id=${projectId}`);
  }
}

export const api = new ApiClient();
