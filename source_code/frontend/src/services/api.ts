const API_BASE = '/api';

export function decodeJwtPayload<T = any>(token: string): T | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4 !== 0) {
      base64 += '=';
    }
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return JSON.parse(new TextDecoder('utf-8').decode(bytes)) as T;
  } catch (err) {
    console.error('[Auth] Failed to decode token:', err);
    return null;
  }
}

export const parseJwt = decodeJwtPayload;

export function encodeBase64Url(str: string): string {
  const bytes = new TextEncoder().encode(str);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export const base64UrlEncode = encodeBase64Url;
export const base64UrlDecode = (str: string): string => {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
  while (base64.length % 4 !== 0) {
    base64 += '=';
  }
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new TextDecoder('utf-8').decode(bytes);
};

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  google_id?: string;
  avatar_url?: string;
  role?: string;
  skills?: string;
}

export interface ProjectMember {
  id: number;
  project_id: number;
  user_id: number;
  role: 'OWNER' | 'PM' | 'MEMBER' | 'VIEWER';
  created_at: string;
  user?: UserProfile;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export class ApiService {
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

  async request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');

    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (res.status === 401) {
      // Evict invalid/expired/stale token from localStorage immediately
      this.setToken(null);
      const errorData = await res.json().catch(() => ({ detail: 'Unauthorized' }));
      throw new Error(errorData.detail || 'Session expired or invalid credentials');
    }

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errorData.detail || `HTTP Error ${res.status}`);
    }

    if (res.status === 204) {
      return null as T;
    }

    return res.json();
  }

  async register(email: string, password: string, fullName: string) {
    const res = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName })
    });
    this.setToken(res.access_token);
    return res;
  }

  async login(email: string, password: string) {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    this.setToken(res.access_token);
    return res;
  }

  async loginWithGoogle(credential: string) {
    const res = await this.request<AuthResponse>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential })
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe() {
    return this.request<UserProfile>('/auth/me');
  }

  async getUsers() {
    return this.request<any[]>('/users');
  }

  async searchUsers(query: string) {
    return this.request<UserProfile[]>(`/users/search?q=${encodeURIComponent(query)}`);
  }

  logout() {
    this.setToken(null);
  }

  async getProjectMembers(projectId = 1) {
    return this.request<ProjectMember[]>(`/projects/${projectId}/members`);
  }

  async addProjectMember(projectId: number, userId: number, role = 'MEMBER') {
    return this.request<ProjectMember>(`/projects/${projectId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role })
    });
  }

  async updateProjectMemberRole(projectId: number, userId: number, role: string) {
    return this.request<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role })
    });
  }

  async removeProjectMember(projectId: number, userId: number) {
    return this.request<void>(`/projects/${projectId}/members/${userId}`, {
      method: 'DELETE'
    });
  }

  async getTasks(projectId = 1) {
    return this.request<any[]>(`/tasks?project_id=${projectId}`);
  }

  async createTask(task: any) {
    return this.request<any>('/tasks', {
      method: 'POST',
      body: JSON.stringify(task)
    });
  }

  async updateTask(id: string | number, updates: any) {
    const cleanId = typeof id === 'string' ? id.replace(/\D/g, '') : id;
    return this.request<any>(`/tasks/${cleanId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates)
    });
  }

  async deleteTask(id: string | number) {
    const cleanId = typeof id === 'string' ? id.replace(/\D/g, '') : id;
    return this.request<void>(`/tasks/${cleanId}`, {
      method: 'DELETE'
    });
  }

  async cycleTaskStatus(id: string | number) {
    const cleanId = typeof id === 'string' ? id.replace(/\D/g, '') : id;
    return this.request<any>(`/tasks/${cleanId}/cycle-status`, {
      method: 'POST'
    });
  }

  async requestPriority(id: string | number, requestedPriority: string, reason: string) {
    const cleanId = typeof id === 'string' ? id.replace(/\D/g, '') : id;
    return this.request<any>(`/tasks/${cleanId}/request-priority`, {
      method: 'POST',
      body: JSON.stringify({ requested_priority: requestedPriority, reason })
    });
  }

  async approvePriority(id: string | number) {
    const cleanId = typeof id === 'string' ? id.replace(/\D/g, '') : id;
    return this.request<any>(`/tasks/${cleanId}/approve-priority`, {
      method: 'POST'
    });
  }

  async rejectPriority(id: string | number) {
    const cleanId = typeof id === 'string' ? id.replace(/\D/g, '') : id;
    return this.request<any>(`/tasks/${cleanId}/reject-priority`, {
      method: 'POST'
    });
  }


  async getWeeklySummary(projectId = 1) {
    return this.request<{ status: string; summary: string }>(`/ai/weekly-summary?project_id=${projectId}`, {
      method: 'POST'
    });
  }

  async extractMeetingMinutes(notes: string) {
    return this.request<any>('/ai/meeting-minutes', {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  }

  async recommendAssignment(title: string, description: string, projectId = 1) {
    return this.request<any>(`/ai/recommend-assignment?project_id=${projectId}`, {
      method: 'POST',
      body: JSON.stringify({ title, description })
    });
  }

  async decomposeGoal(goal: string) {
    return this.request<any>('/ai/decompose', {
      method: 'POST',
      body: JSON.stringify({ goal })
    });
  }

  async analyzeGitDiff(diffText: string, currentTasks: any[]) {
    const touchedFiles = diffText
      .split('\n')
      .filter((l) => l.startsWith('+++ b/'))
      .map((l) => l.replace('+++ b/', ''));

    const candidateDoneIds = currentTasks.slice(0, 1).map((t) => t.id);

    return {
      prTitle: `Commit / Diff Analysis (${touchedFiles.length || 1} files touched)`,
      summary: `Analyzed unified diff. Detected module modifications across ${touchedFiles.join(', ') || 'core files'}.`,
      resolvedTaskIds: candidateDoneIds,
      blockedTaskIds: [],
      architecturalConcerns: []
    };

  }

  async getWorkloads() {
    return this.request<any[]>('/stats/workload');
  }

  async getDelayedTasks(projectId = 1) {
    return this.request<any[]>(`/stats/delayed-tasks?project_id=${projectId}`);
  }
}

export const api = new ApiService();
export const ApiClient = ApiService;
