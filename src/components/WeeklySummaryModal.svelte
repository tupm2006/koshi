<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../services/api';
  import { Sparkles, X, Copy, Check, RefreshCw, AlertCircle } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let summaryText = $state<string>('');
  let isLoading = $state<boolean>(true);
  let isCopied = $state<boolean>(false);
  let errorMsg = $state<string | null>(null);

  async function loadSummary() {
    isLoading = true;
    errorMsg = null;
    try {
      const res = await api.getWeeklySummary(1);
      summaryText = res.summary;
    } catch (e: any) {
      errorMsg = e.message || 'Failed to generate weekly summary';
    } finally {
      isLoading = false;
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(summaryText);
    isCopied = true;
    setTimeout(() => (isCopied = false), 2000);
  }

  onMount(() => {
    loadSummary();
  });
</script>

<div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[85vh]">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
          <Sparkles class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">Weekly Project Progress Summary</h2>
          <p class="text-[11px] text-zinc-400">Mandated Feature A: Status & risk report generation</p>
        </div>
      </div>
      <button class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-3 text-xs">
      {#if isLoading}
        <div class="flex flex-col items-center justify-center py-16 text-center">
          <RefreshCw class="w-6 h-6 text-indigo-400 animate-spin mb-3" />
          <p class="text-xs text-zinc-400 font-mono">Aggregating live task data & generating AI report...</p>
        </div>
      {:else if errorMsg}
        <div class="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 flex items-center gap-2 font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      {:else}
        <div class="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 whitespace-pre-wrap font-sans text-zinc-200 leading-relaxed text-xs">
          {summaryText}
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <div class="pt-3 border-t border-zinc-800 flex items-center justify-between">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-mono text-xs cursor-pointer transition"
        onclick={loadSummary}
        disabled={isLoading}
      >
        <RefreshCw class="w-3.5 h-3.5 {isLoading ? 'animate-spin' : ''}" />
        <span>Regenerate</span>
      </button>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 font-mono font-medium text-xs cursor-pointer transition"
          onclick={handleCopy}
          disabled={isLoading || !summaryText}
        >
          {#if isCopied}
            <Check class="w-3.5 h-3.5 text-emerald-600" />
            <span>Copied!</span>
          {:else}
            <Copy class="w-3.5 h-3.5" />
            <span>Copy Report</span>
          {/if}
        </button>
      </div>
    </div>
  </div>
</div>
