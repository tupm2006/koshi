<script setup lang="ts">
import { Keyboard, X } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const SHORTCUTS = [
  { key: 't', desc: 'Toggle Light / Dark Theme Mode' },
  { key: 'j / ↓', desc: 'Select Next Task' },
  { key: 'k / ↑', desc: 'Select Previous Task' },
  { key: 'Space', desc: 'Cycle Task Status (TODO → IN_PROGRESS → BLOCKED → DONE)' },
  { key: 'Enter', desc: 'Inline Rename / Title Edit' },
  { key: 'd / Backspace', desc: 'Delete Selected Task' },
  { key: '1, 2, 3, 4', desc: 'Set Priority (LOW, MEDIUM, HIGH, CRITICAL)' },
  { key: 'c', desc: 'Open Task Creation Dialog' },
  { key: '/', desc: 'Quick Filter / Search' },
  { key: 'a', desc: 'Open AI Goal Decomposer' },
  { key: 'g', desc: 'Open Git Diff Parser' },
  { key: 'v', desc: 'Open DAG Visualizer & Critical Path' },
  { key: '?', desc: 'Show this Shortcuts Cheat Sheet' },
  { key: 'Esc', desc: 'Exit editing / Dismiss dialogs' },
];
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="bg-white dark:bg-slate-900 w-full max-w-lg rounded-2xl p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-slate-100 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 text-slate-800 dark:text-zinc-200">
            <Keyboard class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">Keyboard Navigation Engine</h2>
            <p class="text-[11px] text-slate-500 dark:text-zinc-400">Zero-latency Vim keybindings</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-zinc-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="py-4 space-y-2 text-xs divide-y divide-slate-100 dark:divide-zinc-800/60 max-h-[60vh] overflow-y-auto">
        <div
          v-for="s in SHORTCUTS"
          :key="s.key"
          class="pt-2 flex items-center justify-between font-mono"
        >
          <kbd class="px-2 py-1 rounded bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 text-slate-800 dark:text-zinc-200 text-[11px] font-bold">
            {{ s.key }}
          </kbd>
          <span class="text-slate-600 dark:text-zinc-400 font-sans text-xs">{{ s.desc }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
