<script lang="ts">
  import { decomposeGoalDeterministically } from '../lib/aiDecomposer';
  import { taskStore } from '../stores/taskStore.svelte';
  import type { DecomposedTaskResult, Task } from '../types/task';
  import { Sparkles, X, Check, ArrowRight, Layers, ShieldCheck } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let goalInput = $state('');
  let result = $state<DecomposedTaskResult | null>(null);
  let isProcessing = $state(false);

  function handleDecompose() {
    if (!goalInput.trim()) return;
    isProcessing = true;
    setTimeout(() => {
      result = decomposeGoalDeterministically(goalInput);
      isProcessing = false;
    }, 120);
  }

  function handleCommitAll() {
    if (!result) return;
    const now = Date.now();
    const createdTasks: Task[] = [];
    const titleToIdMap = new Map<string, string>();

    result.subtasks.forEach((st, idx) => {
      const id = `TSK-${taskStore.tasks.length + 101 + idx}`;
      titleToIdMap.set(st.title, id);
    });

    result.subtasks.forEach((st, idx) => {
      const id = `TSK-${taskStore.tasks.length + 101 + idx}`;
      const deps: string[] = [];
      if (st.dependsOnTitles) {
        for (const depTitle of st.dependsOnTitles) {
          const depId = titleToIdMap.get(depTitle);
          if (depId) deps.push(depId);
        }
      }

      createdTasks.push({
        id,
        title: st.title,
        description: st.description,
        status: 'TODO',
        priority: st.priority,
        complexity: st.complexity,
        acceptanceCriteria: st.acceptanceCriteria,
        dependencies: deps,
        createdAt: now + idx * 10,
        updatedAt: now + idx * 10,
      });
    });

    taskStore.addBatchTasks(createdTasks);
    onClose();
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<!-- Modal Backdrop -->
<div class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel glass-panel-glow w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[90vh] overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
          <Sparkles class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-base font-bold text-zinc-100">Deterministic AI Task Decomposer</h2>
          <p class="text-xs text-zinc-400">JSON-schema enforced goal breakdown with dependencies and acceptance criteria</p>
        </div>
      </div>
      <button
        class="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer min-h-[40px]"
        onclick={onClose}
      >
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4">
      <div>
        <label for="goal-input" class="block text-xs font-mono font-medium text-zinc-300 mb-1.5">
          Engineering Goal or Feature Specification:
        </label>
        <div class="flex gap-2">
          <input
            id="goal-input"
            type="text"
            bind:value={goalInput}
            placeholder="e.g., Implement biometric WebAuthn auth flow with fallback"
            class="flex-1 bg-zinc-900/90 border border-zinc-700 rounded-xl px-3.5 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 font-sans min-h-[44px]"
            onkeydown={(e) => e.key === 'Enter' && handleDecompose()}
            autofocus
          />
          <button
            class="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer transition disabled:opacity-50 min-h-[44px]"
            onclick={handleDecompose}
            disabled={!goalInput.trim() || isProcessing}
          >
            {isProcessing ? 'Compiling...' : 'Decompose'}
          </button>
        </div>
      </div>

      {#if result}
        <div class="space-y-3 pt-2">
          <div class="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/20 flex items-start gap-2.5">
            <ShieldCheck class="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <p class="text-xs text-indigo-200/90 leading-relaxed">{result.rationale}</p>
          </div>

          <div class="space-y-2.5">
            <div class="text-[11px] font-mono uppercase text-zinc-400 tracking-wider">
              Generated Subtask DAG ({result.subtasks.length} items):
            </div>
            {#each result.subtasks as st, idx}
              <div class="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-semibold text-zinc-200">{idx + 1}. {st.title}</span>
                  <div class="flex items-center gap-1.5">
                    <span class="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px] text-zinc-300">
                      {st.complexity}
                    </span>
                    <span class="px-2 py-0.5 rounded font-mono text-[10px] {st.priority === 'CRITICAL' ? 'bg-red-500/20 text-red-300' : 'bg-blue-500/20 text-blue-300'}">
                      {st.priority}
                    </span>
                  </div>
                </div>
                <p class="text-xs text-zinc-400">{st.description}</p>
                {#if st.acceptanceCriteria.length > 0}
                  <div class="mt-1 pt-1.5 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
                    <span class="font-mono text-[10px] text-zinc-400 font-medium">Acceptance Criteria:</span>
                    <ul class="list-disc list-inside space-y-0.5 text-zinc-300">
                      {#each st.acceptanceCriteria as ac}
                        <li>{ac}</li>
                      {/each}
                    </ul>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <div class="pt-4 border-t border-zinc-800 flex items-center justify-between">
      <span class="text-xs text-zinc-400 font-mono">Zero hallucination / schema-validated</span>
      <div class="flex items-center gap-2">
        <button
          class="px-3.5 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium cursor-pointer min-h-[44px]"
          onclick={onClose}
        >
          Cancel
        </button>
        {#if result}
          <button
            class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold cursor-pointer transition shadow-lg shadow-emerald-600/20 flex items-center gap-1.5 min-h-[44px]"
            onclick={handleCommitAll}
          >
            <Check class="w-4 h-4" />
            <span>Commit to Backlog</span>
          </button>
        {/if}
      </div>
    </div>
  </div>
</div>
