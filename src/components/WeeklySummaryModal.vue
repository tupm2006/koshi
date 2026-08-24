<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../services/api';
import { Sparkles, X, Copy, Check, RefreshCw, AlertCircle } from 'lucide-vue-next';

defineProps<{
  onClose: () => void;
}>();

const summaryText = ref<string>('');
const isLoading = ref<boolean>(true);
const isCopied = ref<boolean>(false);
const errorMsg = ref<string | null>(null);

async function loadSummary() {
  isLoading.value = true;
  errorMsg.value = null;
  try {
    const res = await api.getWeeklySummary(1);
    summaryText.value = res.summary;
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to generate weekly summary';
  } finally {
    isLoading.value = false;
  }
}

function handleCopy() {
  navigator.clipboard.writeText(summaryText.value);
  isCopied.value = true;
  setTimeout(() => (isCopied.value = false), 2000);
}

onMounted(() => {
  loadSummary();
});
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[85vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400">
            <Sparkles class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">Weekly Project Progress Summary</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Mandated Feature A: Status & risk report generation</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="onClose">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto py-4 space-y-3 text-xs">
        <div v-if="isLoading" class="flex flex-col items-center justify-center py-16 text-center">
          <RefreshCw class="w-6 h-6 text-indigo-600 dark:text-indigo-400 animate-spin mb-3" />
          <p class="text-xs text-slate-500 dark:text-slate-400 font-mono">Aggregating live task data & generating AI report...</p>
        </div>
        <div v-else-if="errorMsg" class="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-2 font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>
        <div v-else class="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 whitespace-pre-wrap font-sans text-slate-800 dark:text-slate-200 leading-relaxed text-xs">
          {{ summaryText }}
        </div>
      </div>

      <!-- Footer -->
      <div class="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-mono text-xs cursor-pointer transition"
          @click="loadSummary"
          :disabled="isLoading"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="isLoading ? 'animate-spin' : ''" />
          <span>Regenerate</span>
        </button>

        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-900 dark:bg-zinc-100 hover:bg-slate-800 dark:hover:bg-white text-white dark:text-zinc-950 font-mono font-medium text-xs cursor-pointer transition shadow-xs"
          @click="handleCopy"
          :disabled="isLoading || !summaryText"
        >
          <Check v-if="isCopied" class="w-3.5 h-3.5 text-emerald-400" />
          <Copy v-else class="w-3.5 h-3.5" />
          <span>{{ isCopied ? 'Copied!' : 'Copy Report' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
