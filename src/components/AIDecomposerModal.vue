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
  <div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="glass-panel w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
            <Sparkles class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">Autonomous Goal Decomposer</h2>
            <p class="text-[11px] text-zinc-400">Transform natural language epics into structured subtasks & DAGs</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Input Area -->
      <div class="py-4 space-y-3">
        <div class="flex gap-2">
          <input
            v-model="goalInput"
            type="text"
            placeholder="Describe your engineering goal or feature epic..."
            class="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 font-sans min-h-[44px]"
            @keydown.enter="handleDecompose()"
          />
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer transition shadow-sm disabled:opacity-50 min-h-[44px]"
            :disabled="isLoading || !goalInput.trim()"
            @click="handleDecompose()"
          >
            <RefreshCw v-if="isLoading" class="w-4 h-4 animate-spin" />
            <Sparkles v-else class="w-4 h-4" />
            <span>{{ isLoading ? 'Decomposing...' : 'Decompose' }}</span>
          </button>
        </div>

        <!-- Quick Prompts -->
        <div class="flex flex-wrap gap-1.5 items-center pt-1">
          <span class="text-[10px] text-zinc-500 font-mono">Presets:</span>
          <button
            v-for="s in SUGGESTIONS"
            :key="s"
            type="button"
            class="text-[10px] font-mono px-2 py-1 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-zinc-200 transition cursor-pointer"
            @click="handleDecompose(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Result Area -->
      <div class="flex-1 overflow-y-auto space-y-3 pr-1">
        <div v-if="errorMsg" class="p-3 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 flex items-center gap-2 text-xs font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>

        <div v-if="result" class="space-y-3">
          <div class="p-3 rounded-xl bg-zinc-900 border border-zinc-800">
            <h3 class="text-xs font-bold text-zinc-200 font-mono">{{ result.epicTitle }}</h3>
            <p class="text-xs text-zinc-400 mt-1 leading-relaxed">{{ result.rationale }}</p>
          </div>

          <div class="space-y-2">
            <div
              v-for="(subtask, idx) in result.subtasks"
              :key="idx"
              class="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 flex flex-col gap-1.5"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="font-medium text-xs text-zinc-200 font-sans">{{ subtask.title }}</span>
                <div class="flex items-center gap-1.5 shrink-0 font-mono text-[10px]">
                  <span v-if="subtask.complexity" class="px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400">
                    [{{ subtask.complexity }}]
                  </span>
                  <span class="px-1.5 py-0.2 rounded border bg-zinc-900 text-zinc-300 border-zinc-700">
                    {{ subtask.priority }}
                  </span>
                </div>
              </div>
              <p class="text-[11px] text-zinc-400 leading-normal">{{ subtask.description }}</p>
              <div v-if="subtask.dependsOnTitles && subtask.dependsOnTitles.length > 0" class="text-[10px] text-indigo-400 font-mono flex items-center gap-1">
                <ArrowRight class="w-3 h-3" />
                <span>Depends on: {{ subtask.dependsOnTitles.join(', ') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div v-if="result" class="pt-4 border-t border-zinc-800 flex items-center justify-end gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 font-mono text-xs cursor-pointer transition min-h-[40px]"
          @click="emit('close')"
        >
          Dismiss
        </button>
        <button
          type="button"
          class="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer transition shadow-md min-h-[40px] disabled:opacity-50"
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
