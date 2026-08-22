<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../services/api';
  import { Users, X, Sparkles, UserCheck, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let taskTitle = $state<string>('Implement Redis Distributed Caching Layer');
  let taskDesc = $state<string>('Configure Redis cluster with cache invalidation rules and hit-rate telemetry.');
  let workloads = $state<any[]>([]);
  let recommendation = $state<any | null>(null);
  let isLoadingRec = $state<boolean>(false);
  let isLoadingWorkload = $state<boolean>(true);

  async function loadWorkloads() {
    isLoadingWorkload = true;
    try {
      workloads = await api.getWorkloads();
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingWorkload = false;
    }
  }

  async function handleRecommend() {
    if (!taskTitle.trim()) return;
    isLoadingRec = true;
    try {
      const res = await api.recommendAssignment(taskTitle, taskDesc, 1);
      recommendation = res.recommendation;
    } catch (e) {
      console.error(e);
    } finally {
      isLoadingRec = false;
    }
  }

  onMount(() => {
    loadWorkloads();
    handleRecommend();
  });
</script>

<div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[88vh]">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
          <Users class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">Skill & Workload-Based Assignment Recommendation</h2>
          <p class="text-[11px] text-zinc-400">Mandated Feature C: Workload distribution & smart task routing</p>
        </div>
      </div>
      <button class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
      <!-- Team Capacity / Workload Grid -->
      <div>
        <h3 class="font-mono text-zinc-400 font-semibold mb-2 uppercase text-[10px] tracking-wider">Current Team Workload & Skills:</h3>
        {#if isLoadingWorkload}
          <div class="py-4 text-center text-zinc-500 font-mono">Loading team profiles...</div>
        {:else}
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {#each workloads as w}
              <div class="p-3 rounded-xl bg-zinc-900 border {w.is_overloaded ? 'border-rose-800/80 bg-rose-950/20' : 'border-zinc-800'} flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-zinc-200 font-mono text-xs">{w.full_name}</span>
                  {#if w.is_overloaded}
                    <span class="flex items-center gap-1 text-[10px] font-mono text-rose-400 font-semibold">
                      <AlertTriangle class="w-3 h-3" /> Overloaded
                    </span>
                  {:else}
                    <span class="flex items-center gap-1 text-[10px] font-mono text-emerald-400 font-medium">
                      <ShieldCheck class="w-3 h-3" /> Optimal
                    </span>
                  {/if}
                </div>
                <div class="flex items-center gap-3 text-zinc-400 font-mono text-[11px]">
                  <span>Tasks: <strong class="text-zinc-200">{w.active_tasks_count}</strong></span>
                  <span>Complexity: <strong class="text-zinc-200">{w.total_complexity_points} pts</strong></span>
                </div>
                <div class="flex flex-wrap gap-1 mt-1">
                  {#each w.skills as skill}
                    <span class="px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 text-[10px] font-mono">
                      {skill}
                    </span>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Test Recommendation Inputs -->
      <div class="pt-2 border-t border-zinc-800 space-y-2.5">
        <h3 class="font-mono text-zinc-400 font-semibold uppercase text-[10px] tracking-wider">Test Task Assignment Recommendation:</h3>
        <div>
          <label for="task-assign-title" class="block text-zinc-300 font-mono text-[11px] mb-1 font-medium">Task Title</label>
          <input
            id="task-assign-title"
            type="text"
            bind:value={taskTitle}
            class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-amber-500 font-sans"
          />
        </div>
        <div>
          <label for="task-assign-desc" class="block text-zinc-300 font-mono text-[11px] mb-1 font-medium">Task Description & Requirements</label>
          <input
            id="task-assign-desc"
            type="text"
            bind:value={taskDesc}
            class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-amber-500 font-sans"
          />
        </div>
        <button
          type="button"
          class="w-full py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-zinc-950 font-mono font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition disabled:opacity-50"
          onclick={handleRecommend}
          disabled={isLoadingRec || !taskTitle.trim()}
        >
          {#if isLoadingRec}
            <RefreshCw class="w-4 h-4 animate-spin text-zinc-950" />
            <span>Evaluating Workloads & Skill Graph...</span>
          {:else}
            <Sparkles class="w-4 h-4 text-zinc-950" />
            <span>Generate AI Recommendation</span>
          {/if}
        </button>
      </div>

      <!-- Recommendation Result Box -->
      {#if recommendation}
        <div class="p-3.5 rounded-xl bg-amber-950/20 border border-amber-800/50 space-y-2 animate-in fade-in">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UserCheck class="w-4 h-4 text-amber-400" />
              <span class="font-mono text-zinc-400 text-[11px]">Recommended Assignee:</span>
              <strong class="text-amber-300 text-xs font-mono">{recommendation.recommended_name}</strong>
            </div>
          </div>
          <p class="text-zinc-300 text-xs leading-relaxed">{recommendation.rationale}</p>
          {#if recommendation.risk_assessment}
            <div class="text-[11px] text-zinc-400 font-mono pt-1 border-t border-amber-900/30">
              <span class="text-amber-400/80">Risk Assessment:</span> {recommendation.risk_assessment}
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>
