import type { Task } from '../types/task';

/**
 * Topologically sorts tasks based on their dependencies.
 * If A depends on B, B must appear before A.
 */
export function topologicalSort(tasks: Task[]): Task[] {
  const taskMap = new Map<string, Task>();
  const inDegree = new Map<string, number>();
  const adj = new Map<string, string[]>(); // dependency -> list of tasks that depend on it

  for (const t of tasks) {
    taskMap.set(t.id, t);
    inDegree.set(t.id, 0);
    adj.set(t.id, []);
  }

  // Build graph
  for (const t of tasks) {
    const deps = t.dependencies || [];
    for (const depId of deps) {
      if (taskMap.has(depId)) {
        adj.get(depId)!.push(t.id);
        inDegree.set(t.id, (inDegree.get(t.id) || 0) + 1);
      }
    }
  }

  const queue: string[] = [];
  for (const [id, deg] of inDegree.entries()) {
    if (deg === 0) {
      queue.push(id);
    }
  }

  const result: Task[] = [];
  while (queue.length > 0) {
    // Sort queue by priority and dueDate for deterministic high-leverage sequencing
    queue.sort((a, b) => {
      const taskA = taskMap.get(a)!;
      const taskB = taskMap.get(b)!;
      const priorityWeight: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
      const diff = (priorityWeight[taskB.priority] || 0) - (priorityWeight[taskA.priority] || 0);
      if (diff !== 0) return diff;
      if (taskA.dueDate && taskB.dueDate) return taskA.dueDate.localeCompare(taskB.dueDate);
      return taskA.createdAt - taskB.createdAt;
    });

    const currId = queue.shift()!;
    result.push(taskMap.get(currId)!);

    const neighbors = adj.get(currId) || [];
    for (const nextId of neighbors) {
      const newDeg = (inDegree.get(nextId) || 1) - 1;
      inDegree.set(nextId, newDeg);
      if (newDeg === 0) {
        queue.push(nextId);
      }
    }
  }

  // Handle any remaining tasks in cycles
  if (result.length < tasks.length) {
    for (const t of tasks) {
      if (!result.some((r) => r.id === t.id)) {
        result.push(t);
      }
    }
  }

  return result;
}

/**
 * Computes the critical path (longest chain of unfinished dependencies with high priority / tight deadlines).
 */
export function computeCriticalPath(tasks: Task[]): Set<string> {
  const taskMap = new Map<string, Task>();
  const activeTasks = tasks.filter((t) => t.status !== 'DONE');
  for (const t of activeTasks) {
    taskMap.set(t.id, t);
  }

  const complexityWeight: Record<string, number> = { XL: 8, L: 5, M: 3, S: 1 };
  const priorityWeight: Record<string, number> = { CRITICAL: 10, HIGH: 5, MEDIUM: 2, LOW: 1 };

  // Longest path dynamic programming.
  //
  // The memo is only safe for results that were computed without truncation.
  // When a walk stops early at an already-visited node (i.e. a cycle), the value
  // depends on *how we got there*, not just on the node — caching it would let a
  // truncated result leak into an unrelated traversal and make the critical path
  // depend on array order. Such results are returned but never cached (F-24).
  const memo = new Map<string, { weight: number; path: string[] }>();

  interface PathResult {
    weight: number;
    path: string[];
    /** True when a cycle cut this walk short, making the result context-specific. */
    truncated: boolean;
  }

  function getPathWeight(taskId: string, visited = new Set<string>()): PathResult {
    if (visited.has(taskId)) return { weight: 0, path: [], truncated: true };

    const cached = memo.get(taskId);
    if (cached) return { ...cached, truncated: false };

    const task = taskMap.get(taskId);
    if (!task) return { weight: 0, path: [], truncated: false };

    visited.add(taskId);
    const selfWeight = (priorityWeight[task.priority] || 1) * (complexityWeight[task.complexity || 'M'] || 3);

    let maxDepWeight = 0;
    let bestDepPath: string[] = [];
    let sawTruncation = false;

    const deps = task.dependencies || [];
    for (const depId of deps) {
      if (taskMap.has(depId)) {
        const sub = getPathWeight(depId, new Set(visited));
        if (sub.truncated) sawTruncation = true;
        if (sub.weight > maxDepWeight) {
          maxDepWeight = sub.weight;
          bestDepPath = sub.path;
        }
      }
    }

    const res = { weight: selfWeight + maxDepWeight, path: [...bestDepPath, taskId] };
    if (!sawTruncation) memo.set(taskId, res);
    return { ...res, truncated: sawTruncation };
  }

  let maxChainWeight = -1;
  let criticalPathIds: string[] = [];

  for (const t of activeTasks) {
    const chain = getPathWeight(t.id);
    if (chain.weight > maxChainWeight) {
      maxChainWeight = chain.weight;
      criticalPathIds = chain.path;
    }
  }

  return new Set(criticalPathIds);
}
