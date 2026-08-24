<script setup lang="ts">
import { useTaskStore } from '../stores/taskStore';
import { GitFork, X, Flame, ArrowRight } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-3xl rounded-lg p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[85vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-600 dark:text-rose-400">
            <GitFork class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">DAG Execution Order & Critical Path</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Topological Sort graph & unblock sequencing</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
        <div class="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <span class="font-mono text-slate-600 dark:text-slate-400">Critical Path Tasks:</span>
          <span class="px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800 font-mono font-bold text-xs flex items-center gap-1">
            <Flame class="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
            <span>{{ taskStore.criticalPathIds.size }} Bottlenecks</span>
          </span>
        </div>

        <div class="space-y-2">
          <h4 class="font-mono text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider font-semibold">Topological Execution Pipeline:</h4>
          <div class="space-y-2">
            <div
              v-for="(task, idx) in taskStore.dagOrder"
              :key="task.id"
              class="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/60 border flex items-center justify-between gap-3"
              :class="taskStore.criticalPathIds.has(task.id) ? 'border-rose-300 bg-rose-50 dark:border-rose-800/80 dark:bg-rose-950/20' : 'border-slate-200 dark:border-slate-800'"
            >
              <div class="flex items-center gap-2.5 min-w-0">
                <span class="font-mono text-slate-400 dark:text-slate-500 font-bold w-5">{{ idx + 1 }}.</span>
                <span class="font-mono text-slate-500 dark:text-slate-400 text-[11px]">{{ task.id }}</span>
                <span class="font-medium text-slate-800 dark:text-slate-200 truncate">{{ task.title }}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0 font-mono text-[10px]">
                <span v-if="taskStore.criticalPathIds.has(task.id)" class="text-rose-600 dark:text-rose-400 flex items-center gap-1 font-semibold">
                  <Flame class="w-3 h-3" /> Critical
                </span>
                <span class="px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-transparent text-slate-700 dark:text-slate-300">
                  {{ task.status }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
