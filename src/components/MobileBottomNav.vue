<script setup lang="ts">
import { Plus, Search, Sparkles, GitFork, GitPullRequest } from 'lucide-vue-next';

defineProps<{
  onOpenCreate: () => void;
  onOpenAIDecomposer: () => void;
  onOpenDAG: () => void;
  onOpenGitDiff: () => void;
  onFocusSearch: () => void;
}>();
</script>

<template>
  <!-- Bottom Floating Thumb Bar for Mobile (< md breakpoint) -->
  <nav class="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-slate-900/90 border-t border-slate-200 dark:border-slate-800 backdrop-blur-xl safe-bottom px-3 py-1.5 shadow-2xl">
    <div class="grid grid-cols-5 items-center gap-1">
      <button
        type="button"
        class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 active:bg-slate-200 dark:active:bg-slate-800 transition min-h-[44px] cursor-pointer"
        @click="onFocusSearch"
        title="Search (/)"
      >
        <Search class="w-4 h-4" />
        <span class="text-[9px] mt-0.5 font-mono">Search</span>
      </button>

      <button
        type="button"
        class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 active:bg-slate-200 dark:active:bg-slate-800 transition min-h-[44px] cursor-pointer"
        @click="onOpenAIDecomposer"
        title="AI Decomposer (a)"
      >
        <Sparkles class="w-4 h-4" />
        <span class="text-[9px] mt-0.5 font-mono">AI</span>
      </button>

      <!-- Center + Button -->
      <div class="flex items-center justify-center">
        <button
          type="button"
          class="w-10 h-10 rounded-lg bg-slate-900 dark:bg-slate-100 hover:bg-slate-800 dark:hover:bg-white text-white dark:text-slate-950 flex items-center justify-center font-bold cursor-pointer active:scale-95 transition shadow-sm"
          @click="onOpenCreate"
          title="Create Task (c)"
        >
          <Plus class="w-5 h-5 stroke-[2.5]" />
        </button>
      </div>

      <button
        type="button"
        class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 active:bg-slate-200 dark:active:bg-slate-800 transition min-h-[44px] cursor-pointer"
        @click="onOpenDAG"
        title="DAG Critical Path (v)"
      >
        <GitFork class="w-4 h-4" />
        <span class="text-[9px] mt-0.5 font-mono">DAG</span>
      </button>

      <button
        type="button"
        class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 active:bg-slate-200 dark:active:bg-slate-800 transition min-h-[44px] cursor-pointer"
        @click="onOpenGitDiff"
        title="Git Diff (g)"
      >
        <GitPullRequest class="w-4 h-4" />
        <span class="text-[9px] mt-0.5 font-mono">Diff</span>
      </button>
    </div>
  </nav>
</template>
