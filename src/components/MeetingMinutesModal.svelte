<script lang="ts">
  import { api } from '../services/api';
  import { FileText, X, Sparkles, Check, RefreshCw, AlertCircle, Calendar, User } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let rawNotes = $state<string>(
    'Họp ngày 22/08/2026:\n- Felix Su phụ trách hoàn thiện backend FastAPI và SQLite trước 18h.\n- Dev Member kiểm tra Svelte 5 runes và giao diện Kanban Board.\n- Đã chốt: Chạy toàn bộ test suite pytest trước khi merge code vào production.'
  );
  let isLoading = $state<boolean>(false);
  let result = $state<{ main_topics: string[]; action_items: any[]; key_decisions: string[] } | null>(null);
  let errorMsg = $state<string | null>(null);

  async function handleExtract() {
    if (!rawNotes.trim()) return;
    isLoading = true;
    errorMsg = null;
    try {
      const res = await api.extractMeetingMinutes(rawNotes);
      result = res;
    } catch (e: any) {
      errorMsg = e.message || 'Failed to extract meeting minutes';
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[88vh]">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
          <FileText class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">Meeting Minutes & Action Items Generator</h2>
          <p class="text-[11px] text-zinc-400">Mandated Feature B: Unstructured meeting notes extraction</p>
        </div>
      </div>
      <button class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
      <div>
        <label for="meeting-notes-input" class="block font-mono text-zinc-300 mb-1.5 font-semibold">Raw Meeting Notes / Transcript *</label>
        <textarea
          id="meeting-notes-input"
          bind:value={rawNotes}
          rows="4"
          placeholder="Paste raw unstructured meeting notes here..."
          class="w-full bg-zinc-900 border border-zinc-700 rounded-xl p-3 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 font-mono"
        ></textarea>
      </div>

      <button
        type="button"
        class="w-full py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer transition shadow-sm disabled:opacity-50"
        onclick={handleExtract}
        disabled={isLoading || !rawNotes.trim()}
      >
        {#if isLoading}
          <RefreshCw class="w-4 h-4 animate-spin" />
          <span>Processing with AI Engine...</span>
        {:else}
          <Sparkles class="w-4 h-4" />
          <span>Extract Structured Minutes</span>
        {/if}
      </button>

      {#if errorMsg}
        <div class="p-3 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 flex items-center gap-2 font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      {/if}

      {#if result}
        <div class="space-y-3 pt-2 border-t border-zinc-800 animate-in fade-in">
          <!-- Main Topics -->
          {#if result.main_topics && result.main_topics.length > 0}
            <div class="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
              <h4 class="font-mono text-zinc-400 font-semibold mb-1.5 uppercase text-[10px] tracking-wider">Main Topics Discussed:</h4>
              <ul class="list-disc list-inside space-y-1 text-zinc-200">
                {#each result.main_topics as topic}
                  <li>{topic}</li>
                {/each}
              </ul>
            </div>
          {/if}

          <!-- Action Items -->
          {#if result.action_items && result.action_items.length > 0}
            <div class="space-y-2">
              <h4 class="font-mono text-zinc-400 font-semibold uppercase text-[10px] tracking-wider">Extracted Action Items:</h4>
              <div class="grid grid-cols-1 gap-2">
                {#each result.action_items as item}
                  <div class="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0"></span>
                      <span class="font-medium text-zinc-200 truncate">{item.title}</span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0 font-mono text-[10px]">
                      <span class="text-zinc-400 flex items-center gap-1">
                        <User class="w-3 h-3 text-zinc-500" />
                        {item.assignee_name || 'Unassigned'}
                      </span>
                      <span class="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                        {item.priority || 'MEDIUM'}
                      </span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Key Decisions -->
          {#if result.key_decisions && result.key_decisions.length > 0}
            <div class="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-emerald-200">
              <h4 class="font-mono text-emerald-400 font-semibold mb-1.5 uppercase text-[10px] tracking-wider">Key Decisions:</h4>
              <ul class="list-disc list-inside space-y-1 text-xs">
                {#each result.key_decisions as dec}
                  <li>{dec}</li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>
