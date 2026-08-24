<script setup lang="ts">
import { ref } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { api } from '../services/api';
import type { GitDiffAnalysisResult } from '../types/task';
import { GitPullRequest, X, Sparkles, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const diffText = ref(
  'diff --git a/src/stores/taskStore.ts b/src/stores/taskStore.ts\n+ export const useTaskStore = defineStore(...)\n- import { writable } from "svelte/store";'
);
const isLoading = ref(false);
const result = ref<GitDiffAnalysisResult | null>(null);
const errorMsg = ref<string | null>(null);
const isApplied = ref(false);

async function handleAnalyze() {
  if (!diffText.value.trim()) return;
  isLoading.value = true;
  errorMsg.value = null;
  result.value = null;
  isApplied.value = false;

  try {
    const res = await api.analyzeGitDiff(diffText.value, taskStore.tasks);
    result.value = res;
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to analyze diff';
  } finally {
    isLoading.value = false;
  }
}

function handleApplyStatuses() {
  if (!result.value) return;
  if (result.value.resolvedTaskIds) {
    for (const id of result.value.resolvedTaskIds) {
      taskStore.setStatus(id, 'DONE');
    }
  }
  if (result.value.blockedTaskIds) {
    for (const b of result.value.blockedTaskIds) {
      taskStore.updateTask(b.id, { status: 'BLOCKED', blockingReason: b.reason });
    }
  }
  isApplied.value = true;
  setTimeout(() => emit('close'), 1200);
}
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-purple-50 dark:bg-purple-500/10 border border-purple-200 dark:border-purple-500/30 text-purple-600 dark:text-purple-400">
            <GitPullRequest class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">Git Diff Analysis & Auto-Resolution</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Map code changes directly to board task states</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto py-4 space-y-3 text-xs">
        <div>
          <label for="vue-git-diff-textarea" class="block font-mono text-slate-700 dark:text-zinc-300 mb-1.5 font-semibold">Unified Git Patch / Diff *</label>
          <textarea
            id="vue-git-diff-textarea"
            v-model="diffText"
            rows="5"
            placeholder="Paste output from `git diff`..."
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-zinc-700 rounded-xl p-3 text-xs font-mono text-slate-900 dark:text-zinc-200 placeholder-slate-400 dark:placeholder-zinc-500 focus:outline-none focus:border-purple-500"
          ></textarea>
        </div>

        <button
          type="button"
          class="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer transition disabled:opacity-50"
          @click="handleAnalyze"
          :disabled="isLoading || !diffText.trim()"
        >
          <RefreshCw v-if="isLoading" class="w-4 h-4 animate-spin" />
          <Sparkles v-else class="w-4 h-4" />
          <span>{{ isLoading ? 'Analyzing Code Semantics...' : 'Analyze Git Diff' }}</span>
        </button>

        <div v-if="errorMsg" class="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-2 font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>

        <div v-if="result" class="space-y-3 pt-2 border-t border-slate-200 dark:border-zinc-800 animate-in fade-in">
          <div class="p-3 rounded-xl bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800">
            <h4 class="font-mono text-slate-900 dark:text-zinc-200 font-bold text-xs">{{ result.prTitle }}</h4>
            <p class="text-slate-600 dark:text-zinc-400 text-xs mt-1">{{ result.summary }}</p>
          </div>

          <div v-if="result.resolvedTaskIds && result.resolvedTaskIds.length > 0" class="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40">
            <span class="font-mono text-emerald-700 dark:text-emerald-400 font-bold text-[11px]">Tasks to Mark DONE:</span>
            <div class="flex flex-wrap gap-1.5 mt-1.5">
              <span v-for="id in result.resolvedTaskIds" :key="id" class="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-800 font-mono text-[10px] font-medium">
                {{ id }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div v-if="result" class="pt-3 border-t border-slate-200 dark:border-zinc-800 flex items-center justify-end gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-xl bg-slate-100 dark:bg-zinc-900 hover:bg-slate-200 dark:hover:bg-zinc-800 text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-200 font-mono text-xs cursor-pointer"
          @click="emit('close')"
        >
          Dismiss
        </button>
        <button
          type="button"
          class="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          :disabled="isApplied"
          @click="handleApplyStatuses"
        >
          <CheckCircle2 class="w-4 h-4" />
          <span>{{ isApplied ? 'Applied to Tasks!' : 'Apply Status Transitions' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
