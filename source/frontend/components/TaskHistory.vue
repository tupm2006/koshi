<script setup lang="ts">
/**
 * Who changed what on a task, newest first (migration 0009). Collapsed by
 * default and loaded on open, so the inspector costs nothing extra until asked.
 * Values are rendered as text, never as markup.
 */
import { ref, computed, watch } from 'vue';
import { api, serverIdOf, type TaskEvent } from '../services/api';
import { useI18nStore } from '../stores/i18nStore';
import type { TranslationKey } from '../lib/translations';
import { History, ChevronDown } from 'lucide-vue-next';

const props = defineProps<{ taskId: string }>();
const i18n = useI18nStore();
const t = computed(() => i18n.t);

const open = ref(false);
const events = ref<TaskEvent[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

async function load() {
  const id = serverIdOf(props.taskId);
  if (id === null) return;
  loading.value = true;
  error.value = null;
  try {
    events.value = await api.getTaskHistory(id);
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

function toggle() {
  open.value = !open.value;
  if (open.value) load();
}

watch(() => props.taskId, () => { if (open.value) load(); });

const KNOWN = ['created', 'title', 'status', 'priority', 'complexity_points', 'due_date', 'blocking_reason', 'sprint_id', 'description', 'assignees'];
const fieldLabel = (f: string) => (KNOWN.includes(f) ? t.value(`history.${f === 'title' ? 'title_' : f}` as TranslationKey) : f);
const when = (iso: string) => new Date(iso.endsWith('Z') ? iso : iso + 'Z').toLocaleString(i18n.locale === 'vi' ? 'vi-VN' : 'en-GB', { dateStyle: 'short', timeStyle: 'short' });
</script>

<template>
  <div data-testid="task-history">
    <button type="button" class="w-full flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer" @click="toggle">
      <History class="w-3.5 h-3.5" /> {{ t('history.title') }}
      <ChevronDown class="w-3.5 h-3.5 ml-auto transition-transform" :class="open ? 'rotate-180' : ''" />
    </button>
    <div v-if="open" class="mt-2 space-y-1.5 text-[11px]">
      <p v-if="loading" class="text-slate-400">…</p>
      <p v-else-if="error" class="text-rose-600">{{ error }}</p>
      <p v-else-if="events.length === 0" class="text-slate-400">{{ t('history.empty') }}</p>
      <div v-for="e in events" :key="e.id" class="flex gap-2" data-history-event>
        <span class="shrink-0 font-mono text-slate-400 w-[92px]">{{ when(e.created_at) }}</span>
        <span class="min-w-0">
          <b class="text-slate-700 dark:text-slate-200">{{ e.actor?.full_name ?? t('history.someone') }}</b>
          <template v-if="e.field === 'created'"> {{ t('history.createdVerb') }}</template>
          <template v-else>
            · {{ fieldLabel(e.field) }}:
            <span class="line-through text-slate-400">{{ e.old_value ?? '—' }}</span>
            → <span class="text-slate-700 dark:text-slate-200">{{ e.new_value ?? '—' }}</span>
          </template>
        </span>
      </div>
    </div>
  </div>
</template>
