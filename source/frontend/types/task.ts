export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'DONE';
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Complexity = 'S' | 'M' | 'L' | 'XL';

/** A person on a task. `id` is the server user id. */
export interface TaskAssignee {
  id: number;
  full_name: string;
  avatar_url?: string | null;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  /**
   * Everyone working on this task. Plural since DEC-023 — one piece of work can
   * need two people, and duplicating the task to say so loses the fact that it
   * is one piece of work.
   */
  assignees?: TaskAssignee[];
  dueDate?: string; // ISO 8601
  blockingReason?: string;
  createdAt: number;
  updatedAt: number;
  // Graph / DAG metadata
  dependencies?: string[]; // IDs of tasks this task depends on
  complexity?: 'S' | 'M' | 'L' | 'XL';
  acceptanceCriteria?: string[];
}

export type FilterStatus = 'ALL' | TaskStatus;
export type FilterPriority = 'ALL' | TaskPriority;

export interface TaskFilter {
  searchQuery: string;
  status: FilterStatus;
  priority: FilterPriority;
  assignee?: string;
  onlyCriticalPath?: boolean;
}

export interface DecomposedTaskResult {
  epicTitle: string;
  rationale: string;
  subtasks: {
    title: string;
    description: string;
    priority: TaskPriority;
    complexity: 'S' | 'M' | 'L' | 'XL';
    acceptanceCriteria: string[];
    dependsOnTitles?: string[];
  }[];
}

export interface GitDiffAnalysisResult {
  prTitle: string;
  summary: string;
  resolvedTaskIds: string[];
  blockedTaskIds: { id: string; reason: string }[];
  architecturalConcerns: string[];
}

export interface DAGNode {
  task: Task;
  level: number;
  isCriticalPath: boolean;
  blockers: Task[];
  dependents: Task[];
}
