<script setup lang="ts">
/**
 * The notification feed.
 *
 * A full screen rather than a dropdown, and part of the `appView` state machine
 * alongside LANDING / BOARD / PROFILE. A dropdown would have to be short enough
 * to hang off a button, which is the wrong shape for a history you scroll.
 *
 * Rendering is driven entirely by `kind`. Nothing here parses a message, and no
 * message is stored server-side: the wording belongs to the client because the
 * client knows the reader's language. Adding a kind means one entry in `LABELS`
 * and nothing else.
 */
import { computed } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { parseSegments } from '../lib/mentions';
import type { AppNotification, NotificationKind } from '../services/api';
import {
  ArrowLeft, Bell, AtSign, CornerDownRight, UserPlus, FolderKanban, Clock, CheckCheck,
} from 'lucide-vue-next';

const taskStore = useTaskStore();

/** One entry per kind. The only place a kind needs to be taught about. */
const LABELS: Record<NotificationKind, { icon: any; verb: string; tone: string }> = {
  MENTION: { icon: AtSign, verb: 'mentioned you in', tone: 'text-indigo-600 dark:text-indigo-400' },
  REPLY: { icon: CornerDownRight, verb: 'replied to you on', tone: 'text-sky-600 dark:text-sky-400' },
  TASK_ASSIGNED: { icon: UserPlus, verb: 'assigned you', tone: 'text-emerald-600 dark:text-emerald-400' },
  PROJECT_INVITED: { icon: FolderKanban, verb: 'invited you to', tone: 'text-amber-600 dark:text-amber-400' },
  TASK_DUE_SOON: { icon: Clock, verb: 'is due soon', tone: 'text-rose-600 dark:text-rose-400' },
};

const unread = computed(() => taskStore.notifications.filter((n) => n.read_at === null).length);

function when(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

/** Mention tokens are stored raw; strip them to a readable name for the feed. */
function plain(excerpt: string | null): string {
  if (!excerpt) return '';
  return parseSegments(excerpt)
    .map((s) => (s.type === 'mention' ? `@${s.label}` : s.value))
    .join('');
}

async function open(n: AppNotification) {
  await taskStore.openNotification(n);
}
</script>

<template>
  <div class="min-h-screen min-h-[100dvh] bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col">
    <header class="border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
      <div class="max-w-3xl mx-auto px-5 h-14 flex items-center justify-between gap-3">
        <button
          type="button"
          id="notifications-back"
          class="inline-flex items-center gap-1.5 text-xs font-mono text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 cursor-pointer"
          @click="taskStore.showBoard()"
        >
          <ArrowLeft class="w-4 h-4" />
          <span>Back to board</span>
        </button>

        <button
          v-if="unread > 0"
          type="button"
          id="notifications-read-all"
          class="inline-flex items-center gap-1.5 text-xs font-mono text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer"
          @click="taskStore.markAllNotificationsRead()"
        >
          <CheckCheck class="w-4 h-4" />
          <span>Mark all as read</span>
        </button>
      </div>
    </header>

    <main class="flex-1 w-full max-w-3xl mx-auto px-5 py-8 space-y-4 overflow-y-auto">
      <h1 class="flex items-center gap-2 text-lg font-semibold font-sans">
        <Bell class="w-5 h-5" />
        <span>Notifications</span>
        <span
          v-if="unread > 0"
          class="px-2 py-0.5 rounded-full bg-rose-600 text-white text-[11px] font-mono font-bold"
        >{{ unread }}</span>
      </h1>

      <p
        v-if="taskStore.notifications.length === 0"
        id="notifications-empty"
        class="p-6 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-center text-xs text-slate-500 dark:text-slate-400"
      >
        Nothing yet. You will hear about mentions and replies here —
        never about your own comments.
      </p>

      <ul v-else class="space-y-2">
        <li v-for="n in taskStore.notifications" :key="n.id">
          <button
            type="button"
            :data-notification="n.id"
            :data-kind="n.kind"
            :data-unread="n.read_at === null"
            class="w-full text-left rounded-xl border p-4 flex items-start gap-3 cursor-pointer transition-colors"
            :class="n.read_at === null
              ? 'bg-white dark:bg-slate-900 border-indigo-300 dark:border-indigo-800/60 hover:border-indigo-400'
              : 'bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 hover:border-slate-300'"
            @click="open(n)"
          >
            <component :is="LABELS[n.kind].icon" class="w-4 h-4 mt-0.5 shrink-0" :class="LABELS[n.kind].tone" />

            <span class="min-w-0 flex-1">
              <span class="block text-xs text-slate-900 dark:text-slate-100">
                <strong class="font-semibold">{{ n.actor?.full_name || 'Someone' }}</strong>
                {{ LABELS[n.kind].verb }}
                <strong v-if="n.task_title" class="font-semibold">{{ n.task_title }}</strong>
                <span v-else-if="n.project_name" class="font-semibold">{{ n.project_name }}</span>
              </span>

              <span
                v-if="n.excerpt"
                class="block mt-1 text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 break-words"
              >{{ plain(n.excerpt) }}</span>

              <span class="block mt-1 text-[10px] font-mono text-slate-500 dark:text-slate-500">
                <template v-if="n.task_key">{{ n.task_key }} · </template>
                <template v-if="n.project_name">{{ n.project_name }} · </template>
                {{ when(n.created_at) }}
              </span>
            </span>

            <span
              v-if="n.read_at === null"
              data-unread-dot
              class="w-2 h-2 mt-1.5 rounded-full bg-indigo-500 shrink-0"
            ></span>
          </button>
        </li>
      </ul>
    </main>
  </div>
</template>
