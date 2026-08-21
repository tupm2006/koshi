import type { GitDiffAnalysisResult, Task } from '../types/task';

/**
 * Deterministically parses Git diffs / commit logs to match task IDs,
 * identify auto-closed blockers, and surface unaddressed edge cases.
 */
export function parseGitDiff(diffText: string, existingTasks: Task[]): GitDiffAnalysisResult {
  const lines = diffText.split('\n');
  const taskMap = new Map(existingTasks.map((t) => [t.id.toLowerCase(), t]));
  const taskTitleMap = new Map(existingTasks.map((t) => [t.title.toLowerCase(), t]));

  const resolvedIds = new Set<string>();
  const blockedTasks: { id: string; reason: string }[] = [];
  const concerns: string[] = [];

  let prTitle = 'PR / Commit Diff Analysis';
  const firstLine = lines.find((l) => l.trim().length > 0) || '';
  if (firstLine.startsWith('#') || firstLine.startsWith('feat:') || firstLine.startsWith('fix:')) {
    prTitle = firstLine.replace(/^#+\s*/, '');
  }

  // Look for issue closing patterns: "closes #TSK-123", "fixes #id", "resolve TSK-1"
  const closeRegex = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:#)?([a-zA-Z0-9_-]+)/gi;
  let match;
  while ((match = closeRegex.exec(diffText)) !== null) {
    const id = match[1].toLowerCase();
    if (taskMap.has(id)) {
      resolvedIds.add(taskMap.get(id)!.id);
    }
  }

  // Scan for TODO, FIXME, HACK, or regression risks in diff added lines
  let hasUnhandledErrors = false;
  let hasHardcodedSecrets = false;
  let hasAnyTypes = false;

  for (const line of lines) {
    if (line.startsWith('+') && !line.startsWith('+++')) {
      const added = line.slice(1);
      if (/TODO|FIXME|HACK|XXX/i.test(added)) {
        concerns.push(`Found unaddressed comment in diff: "${added.trim().slice(0, 60)}"`);
      }
      if (/catch\s*\([^)]*\)\s*\{\s*\}/.test(added) || /catch\s*\{\s*\}/.test(added)) {
        hasUnhandledErrors = true;
      }
      if (/(?:api_key|secret|password|bearer)\s*=\s*['"][a-zA-Z0-9_\-]{8,}['"]/i.test(added)) {
        hasHardcodedSecrets = true;
      }
      if (/:\s*any\b/.test(added)) {
        hasAnyTypes = true;
      }
    }
  }

  if (hasUnhandledErrors) {
    concerns.push('Empty catch block detected (silent failure risk).');
  }
  if (hasHardcodedSecrets) {
    concerns.push('Potential hardcoded secret or token detected in addition lines.');
  }
  if (hasAnyTypes) {
    concerns.push('TypeScript unsafe `any` coercion detected in diff.');
  }

  // Cross-reference existing BLOCKED tasks with touched files/keywords
  for (const task of existingTasks) {
    if (task.status === 'BLOCKED') {
      const words = task.title.toLowerCase().split(/\s+/).filter((w) => w.length > 3);
      const isMentioned = words.some((w) => diffText.toLowerCase().includes(w));
      if (isMentioned && !resolvedIds.has(task.id)) {
        resolvedIds.add(task.id);
      }
    }
  }

  return {
    prTitle,
    summary: `Analyzed ${lines.length} lines of diff across ${existingTasks.length} tracked tasks. Identified ${resolvedIds.size} potential task resolution(s) and ${concerns.length} architectural flags.`,
    resolvedTaskIds: Array.from(resolvedIds),
    blockedTaskIds: blockedTasks,
    architecturalConcerns: concerns.slice(0, 5),
  };
}
