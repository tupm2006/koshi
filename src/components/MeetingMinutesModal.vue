<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../services/api';
import { FileText, X, Sparkles, RefreshCw, AlertCircle, User } from 'lucide-vue-next';

defineProps<{
  onClose: () => void;
}>();

const rawNotes = ref<string>(
  'Họp ngày 22/08/2026:\n- Felix Anderson phụ trách hoàn thiện backend FastAPI và SQLite trước 18h.\n- Dev Member kiểm tra Vue 3 Composition API và giao diện Kanban Board.\n- Đã chốt: Chạy toàn bộ test suite pytest trước khi merge code vào production.'
);
const isLoading = ref<boolean>(false);
const result = ref<{ main_topics: string[]; action_items: any[]; key_decisions: string[] } | null>(null);
const errorMsg = ref<string | null>(null);

async function handleExtract() {
  if (!rawNotes.value.trim()) return;
  isLoading.value = true;
  errorMsg.value = null;
  try {
    const res = await api.extractMeetingMinutes(rawNotes.value);
    result.value = res;
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to extract meeting minutes';
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100"
    @click.self="onClose"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-lg p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[88vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-sky-50 dark:bg-sky-500/10 border border-sky-200 dark:border-sky-500/30 text-sky-600 dark:text-sky-400">
            <FileText class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold text-slate-900 dark:text-slate-100 font-sans">Meeting Minutes Generator</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Extract action items and key decisions from notes</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="onClose">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
        <div>
          <label for="vue-meeting-notes-input" class="block font-mono text-slate-700 dark:text-slate-300 mb-1.5 font-semibold">Raw Meeting Notes / Transcript *</label>
          <textarea
            id="vue-meeting-notes-input"
            v-model="rawNotes"
            rows="4"
            placeholder="Paste raw unstructured meeting notes here..."
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg p-3 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-sky-500 font-mono"
          ></textarea>
        </div>

        <button
          type="button"
          class="w-full py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer transition shadow-xs disabled:opacity-50"
          @click="handleExtract"
          :disabled="isLoading || !rawNotes.trim()"
        >
          <RefreshCw v-if="isLoading" class="w-4 h-4 animate-spin" />
          <Sparkles v-else class="w-4 h-4" />
          <span>{{ isLoading ? 'Processing with AI Engine...' : 'Extract Structured Minutes' }}</span>
        </button>

        <div v-if="errorMsg" class="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-2 font-mono">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>

        <div v-if="result" class="space-y-3 pt-2 border-t border-slate-200 dark:border-slate-800 animate-in fade-in">
          <!-- Main Topics -->
          <div v-if="result.main_topics && result.main_topics.length > 0" class="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <h4 class="font-mono text-slate-500 dark:text-slate-400 font-semibold mb-1.5 uppercase text-[11px] tracking-wider">Main Topics Discussed:</h4>
            <ul class="list-disc list-inside space-y-1 text-slate-800 dark:text-slate-200">
              <li v-for="topic in result.main_topics" :key="topic">{{ topic }}</li>
            </ul>
          </div>

          <!-- Action Items -->
          <div v-if="result.action_items && result.action_items.length > 0" class="space-y-2">
            <h4 class="font-mono text-slate-500 dark:text-slate-400 font-semibold uppercase text-[11px] tracking-wider">Extracted Action Items:</h4>
            <div class="grid grid-cols-1 gap-2">
              <div
                v-for="(item, idx) in result.action_items"
                :key="idx"
                class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2"
              >
                <div class="flex items-center gap-2 min-w-0">
                  <span class="w-1.5 h-1.5 rounded-full bg-sky-500 shrink-0"></span>
                  <span class="font-medium text-slate-800 dark:text-slate-200 truncate">{{ item.title }}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0 font-mono text-[11px]">
                  <span class="text-slate-600 dark:text-slate-400 flex items-center gap-1">
                    <User class="w-3 h-3 text-slate-400 dark:text-slate-500" />
                    {{ item.assignee_name || 'Unassigned' }}
                  </span>
                  <span class="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
                    {{ item.priority || 'MEDIUM' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Key Decisions -->
          <div v-if="result.key_decisions && result.key_decisions.length > 0" class="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 text-emerald-800 dark:text-emerald-200">
            <h4 class="font-mono text-emerald-700 dark:text-emerald-400 font-semibold mb-1.5 uppercase text-[11px] tracking-wider">Key Decisions:</h4>
            <ul class="list-disc list-inside space-y-1 text-xs">
              <li v-for="dec in result.key_decisions" :key="dec">{{ dec }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
