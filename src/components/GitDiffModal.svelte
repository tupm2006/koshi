<script lang="ts">
  import { parseGitDiff } from '../lib/gitParser';
  import { taskStore } from '../stores/taskStore.svelte';
  import type { GitDiffAnalysisResult } from '../types/task';
  import { GitPullRequest, X, Check, AlertTriangle, CheckCircle2, FileCode } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let diffInput = $state(
`feat(runes): migrate state management to Svelte 5 runes
closes #TSK-101
fixes #TSK-105

diff --git a/src/stores/taskStore.svelte.ts b/src/stores/taskStore.svelte.ts
index a1b2c3d..e4f5g6h 100644
--- a/src/stores/taskStore.svelte.ts
+++ b/src/stores/taskStore.svelte.ts
@@ -10,6 +10,12 @@ export class TaskStore {
+  tasks = $state<Task[]>([]);
+  selectedIndex = $state<number>(0);
+  // TODO: Add telemetry hook for latency audit
+  filteredTasks = $derived.by(() => { ... });
`
  );

  let result = $state<GitDiffAnalysisResult | null>(null);

  function handleAnalyze() {
    result = parseGitDiff(diffInput, taskStore.tasks);
  }

  function handleApplyAutoResolutions() {
    if (!result) return;
    for (const id of result.resolvedTaskIds) {
      taskStore.setStatus(id, 'DONE');
    }
    onClose();
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<div class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel glass-panel-glow w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[90vh] overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
          <GitPullRequest class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-base font-bold text-zinc-100">Git / PR Diff Synchronization</h2>
          <p class="text-xs text-zinc-400">Deterministic diff analysis to auto-close blockers and detect code concerns</p>
        </div>
      </div>
      <button class="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer min-h-[40px]" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4">
      <div>
        <label for="diff-textarea" class="block text-xs font-mono font-medium text-zinc-300 mb-1.5">
          Paste Git Diff or Commit Message:
        </label>
        <textarea
          id="diff-textarea"
          bind:value={diffInput}
          rows="6"
          class="w-full bg-zinc-900/90 border border-zinc-700 rounded-xl p-3 text-xs font-mono text-zinc-200 focus:outline-none focus:border-purple-500"
        ></textarea>
        <button
          class="mt-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold cursor-pointer transition min-h-[44px]"
          onclick={handleAnalyze}
        >
          Analyze Diff
        </button>
      </div>

      {#if result}
        <div class="space-y-3 pt-2">
          <div class="p-3 rounded-xl bg-zinc-900/80 border border-zinc-800 text-xs text-zinc-300">
            {result.summary}
          </div>

          {#if result.resolvedTaskIds.length > 0}
            <div class="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
              <div class="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                <CheckCircle2 class="w-4 h-4" />
                <span>Identified Resolutions ({result.resolvedTaskIds.length}):</span>
              </div>
              <div class="flex flex-wrap gap-1.5">
                {#each result.resolvedTaskIds as id}
                  <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-xs font-medium">
                    {id}
                  </span>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.architecturalConcerns.length > 0}
            <div class="p-3 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
              <div class="flex items-center gap-2 text-xs font-semibold text-amber-400">
                <AlertTriangle class="w-4 h-4" />
                <span>Architectural Edge Cases & Warnings:</span>
              </div>
              <ul class="list-disc list-inside space-y-1 text-xs text-amber-200/90">
                {#each result.architecturalConcerns as c}
                  <li>{c}</li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <div class="pt-4 border-t border-zinc-800 flex items-center justify-between">
      <span class="text-xs text-zinc-400 font-mono">AST & Diff heuristic matcher</span>
      <div class="flex items-center gap-2">
        <button class="px-3.5 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium cursor-pointer min-h-[44px]" onclick={onClose}>
          Cancel
        </button>
        {#if result && result.resolvedTaskIds.length > 0}
          <button
            class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold cursor-pointer transition flex items-center gap-1.5 min-h-[44px]"
            onclick={handleApplyAutoResolutions}
          >
            <Check class="w-4 h-4" />
            <span>Auto-Resolve Tasks ({result.resolvedTaskIds.length})</span>
          </button>
        {/if}
      </div>
    </div>
  </div>
</div>
