<script lang="ts">
  import { taskStore } from '../stores/taskStore.svelte';
  import { GitFork, X, Flame, CheckCircle2, Circle, AlertOctagon, ArrowRight } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let sortedTasks = $derived(taskStore.topoSortedTasks);
  let criticalPath = $derived(taskStore.criticalPathIds);
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<div class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel glass-panel-glow w-full max-w-3xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[90vh] overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
          <GitFork class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-base font-bold text-zinc-100">Topological DAG & Critical Path Engine</h2>
          <p class="text-xs text-zinc-400">Deterministic linear execution sequence ordered by dependency constraints</p>
        </div>
      </div>
      <button class="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer min-h-[40px]" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4">
      <div class="p-3 rounded-xl bg-amber-950/20 border border-amber-500/20 flex items-center gap-2.5 text-xs text-amber-200">
        <Flame class="w-4 h-4 text-rose-400 shrink-0" />
        <span>Critical Path items are prioritized to prevent blocker cascades across milestones.</span>
      </div>

      <div class="space-y-2.5">
        {#each sortedTasks as task, idx}
          {@const isCritical = criticalPath.has(task.id)}
          <div class="p-3.5 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-2.5 transition {isCritical ? 'bg-rose-950/20 border-rose-500/40 shadow-sm shadow-rose-500/10' : 'bg-zinc-900/60 border-zinc-800'}">
            <div class="flex items-start md:items-center gap-3">
              <span class="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300 font-mono text-xs flex items-center justify-center shrink-0">
                {idx + 1}
              </span>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-mono text-xs font-semibold text-zinc-300">{task.id}</span>
                  <span class="text-xs font-medium text-zinc-100 {task.status === 'DONE' ? 'line-through text-zinc-500' : ''}">{task.title}</span>
                  {#if isCritical}
                    <span class="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono font-bold flex items-center gap-1">
                      <Flame class="w-3 h-3" /> CRITICAL PATH
                    </span>
                  {/if}
                </div>
                {#if task.dependencies && task.dependencies.length > 0}
                  <div class="text-[11px] text-zinc-400 font-mono mt-0.5 flex items-center gap-1">
                    <ArrowRight class="w-3 h-3 text-zinc-500" />
                    <span>Requires upstream: {task.dependencies.join(', ')}</span>
                  </div>
                {/if}
              </div>
            </div>

            <div class="flex items-center gap-2 self-end md:self-center">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono {task.status === 'DONE' ? 'bg-emerald-500/20 text-emerald-300' : task.status === 'BLOCKED' ? 'bg-amber-500/20 text-amber-300' : 'bg-blue-500/20 text-blue-300'}">
                {task.status}
              </span>
              <span class="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px]">
                {task.priority}
              </span>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Footer -->
    <div class="pt-4 border-t border-zinc-800 flex items-center justify-between">
      <span class="text-xs text-zinc-400 font-mono">Kahn's algorithm DAG resolver</span>
      <button class="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium cursor-pointer min-h-[44px]" onclick={onClose}>
        Close
      </button>
    </div>
  </div>
</div>
