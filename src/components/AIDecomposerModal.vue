<script setup lang="ts">
import { ref } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { api } from '../services/api';
import type { DecomposedTaskResult, TaskPriority } from '../types/task';
import { Sparkles, X, Plus, Check, RefreshCw, AlertCircle, ArrowRight } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const goalInput = ref('');
const isLoading = ref(false);
const result = ref<DecomposedTaskResult | null>(null);
const errorMsg = ref<string | null>(null);
const isInserted = ref(false);

const SUGGESTIONS = [
  'Build OAuth2 Google & GitHub authentication flow',
  'Implement real-time WebSocket presence and collaboration',
  'Deploy production Kubernetes cluster with Helm charts',
  'Port legacy state to Vue 3 Composition API and Pinia store',
];

async function handleDecompose(customGoal?: string) {
  const targetGoal = customGoal || goalInput.value;
  if (!targetGoal.trim()) return;
  if (customGoal) goalInput.value = customGoal;

  isLoading.value = true;
  errorMsg.value = null;
  result.value = null;
  isInserted.value = false;

  try {
    const res = await api.decomposeGoal(targetGoal);
    result.value = res;
  } catch (err: any) {
    errorMsg.value = err.message || 'Decomposition engine failure.';
  } finally {
    isLoading.value = false;
  }
}

function handleAcceptAll() {
  if (!result.value || !result.value.subtasks) return;
  const createdIds: Record<string, string> = {};

  for (const st of result.value.subtasks) {
    const created = taskStore.createTask(st.title, st.priority || 'MEDIUM', 'TODO');
    if (created) {
      createdIds[st.title] = created.id;
      taskStore.updateTask(created.id, {
        description: st.description,
        complexity: st.complexity,
        acceptanceCriteria: st.acceptanceCriteria,
      });
    }
  }

  // Second pass: wire dependencies
  for (const st of result.value.subtasks) {
    if (st.dependsOnTitles && st.dependsOnTitles.length > 0) {
      const myId = createdIds[st.title];
      if (myId) {
        const depIds = st.dependsOnTitles.map((t) => createdIds[t]).filter(Boolean);
        if (depIds.length > 0) {
          taskStore.updateTask(myId, { dependencies: depIds });
        }
      }
    }
  }

  isInserted.value = true;
  setTimeout(() => {
    emit('close');
  }, 1000);
}
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-lg p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400">
            <Sparkles class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">Task Decomposer</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Break down goals into subtasks and dependencies</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Input Area -->
      <div class="py-4 space-y-3">
        <div class="flex gap-2">
          <input
            v-model="goalInput"
            type="text"
            placeholder="Describe your engineering goal or feature..."
            class="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-md px-3.5 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans h-8"
            @keydown.enter="handleDecompose()"
          />
          <button
            type="button"
            class="h-8 px-3.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer transition shadow-xs disabled:opacity-50 shrink-0"
            :disabled="isLoading || !goalInput.trim()"
            @click="handleDecompose()"
          >
            <RefreshCw v-if="isLoading" class="w-3.5 h-3.5 animate-spin" />
            <Sparkles v-else class="w-3.5 h-3.5" />
            <span>{{ isLoading ? 'Decomposing...' : 'Decompose Task' }}</span>
          </button>
        </div>

        <!-- Quick Prompts -->
        <div class="flex flex-wrap gap-1.5 items-center pt-1">
          <span class="text-[10px] text-slate-500 dark:text-slate-400 font-mono">Presets:</span>
          <button
            v-for="s in SUGGESTIONS"
            :key="s"
            type="button"
            class="text-[10px] font-mono px-2 py-1 rounded bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition cursor-pointer"
            @click="handleDecompose(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Result Area -->
      <div class="flex-1 overflow-y-auto space-y-3 pr-1">
        <div v-if="errorMsg" class="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-2 text-xs font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>

        <div v-if="result" class="space-y-3">
          <div class="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <h3 class="text-xs font-bold text-slate-900 dark:text-slate-200 font-mono">{{ result.epicTitle }}</h3>
            <p class="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">{{ result.rationale }}</p>
          </div>

          <div class="space-y-2">
            <div
              v-for="(subtask, idx) in result.subtasks"
              :key="idx"
              class="p-3 rounded-lg bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 flex flex-col gap-1.5"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="font-medium text-xs text-slate-900 dark:text-slate-200 font-sans">{{ subtask.title }}</span>
                <div class="flex items-center gap-1.5 shrink-0 font-mono text-[10px]">
                  <span v-if="subtask.complexity" class="px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 font-medium">
                    [{{ subtask.complexity }}]
                  </span>
                  <span class="px-1.5 py-0.2 rounded border bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700">
                    {{ subtask.priority }}
                  </span>
                </div>
              </div>
              <p class="text-[11px] text-slate-600 dark:text-slate-400 leading-normal">{{ subtask.description }}</p>
              <div v-if="subtask.dependsOnTitles && subtask.dependsOnTitles.length > 0" class="text-[10px] text-indigo-600 dark:text-indigo-400 font-mono flex items-center gap-1">
                <ArrowRight class="w-3 h-3" />
                <span>Depends on: {{ subtask.dependsOnTitles.join(', ') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div v-if="result" class="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 font-mono text-xs cursor-pointer transition min-h-[40px]"
          @click="emit('close')"
        >
          Dismiss
        </button>
        <button
          type="button"
          class="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer transition shadow-xs min-h-[40px] disabled:opacity-50"
          :disabled="isInserted"
          @click="handleAcceptAll"
        >
          <Check v-if="isInserted" class="w-4 h-4 text-emerald-300" />
          <Plus v-else class="w-4 h-4 stroke-[2.5]" />
          <span>{{ isInserted ? 'Inserted into Board!' : `Add ${result.subtasks.length} Subtasks to Board` }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
