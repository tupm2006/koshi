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
  { key: 'a', desc: 'Open Task Decomposer' },
  { key: 'g', desc: 'Open Git Diff Parser' },
  { key: 'v', desc: 'Open DAG Visualizer & Critical Path' },
  { key: '?', desc: 'Show Keyboard Shortcuts' },
  { key: 'Esc', desc: 'Exit editing / Dismiss dialogs' },
];
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="bg-white dark:bg-slate-900 w-full max-w-lg rounded-lg p-5 md:p-6 shadow-2xl border border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200">
            <Keyboard class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">Keyboard Shortcuts</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Global hotkeys and quick actions</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="py-4 space-y-2 text-xs divide-y divide-slate-100 dark:divide-slate-800/60 max-h-[60vh] overflow-y-auto">
        <div
          v-for="s in SHORTCUTS"
          :key="s.key"
          class="pt-2 flex items-center justify-between font-mono"
        >
          <kbd class="h-6 px-2 inline-flex items-center justify-center rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-[11px] font-bold">
            {{ s.key }}
          </kbd>
          <span class="text-slate-600 dark:text-slate-400 font-sans text-xs">{{ s.desc }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
