<script setup lang="ts">
import { Clock, Pencil, Flame, AlertCircle } from 'lucide-vue-next';
import type { Task, TaskPriority } from '../types/task';

const props = defineProps<{
  task: Task;
  isSelected?: boolean;
  isCriticalPath?: boolean;
}>();

const emit = defineEmits<{
  (e: 'select', task: Task): void;
  (e: 'openDetail', task: Task): void;
  (e: 'cycleStatus', task: Task, direction: 'prev' | 'next'): void;
}>();

function onCardClick() {
  emit('select', props.task);
}

function onCardDblClick() {
  emit('openDetail', props.task);
}

function onEditClick(event: MouseEvent) {
  event.stopPropagation();
  emit('openDetail', props.task);
}

function onStatusCycle(event: MouseEvent, direction: 'prev' | 'next') {
  event.stopPropagation();
  emit('cycleStatus', props.task, direction);
}

function getPriorityBadge(p: TaskPriority) {
  switch (p) {
    case 'CRITICAL':
      return 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/80 font-bold';
    case 'HIGH':
      return 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800/60 font-semibold';
    case 'MEDIUM':
      return 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/40 font-medium';
    case 'LOW':
    default:
      return 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-900 dark:text-slate-400 dark:border-slate-800 font-medium';
  }
}
</script>

<template>
  <div
    @click="onCardClick"
    @dblclick="onCardDblClick"
    :class="[
      'group rounded-md p-3 shadow-xs cursor-grab active:cursor-grabbing select-none border transition-all',
      isSelected
        ? 'ring-2 ring-inset ring-indigo-500 dark:ring-indigo-400 border-indigo-500 dark:border-indigo-400 bg-slate-50 dark:bg-slate-800/90 shadow-sm'
        : 'border-slate-300 dark:border-slate-700/80 bg-white dark:bg-slate-900 hover:border-slate-400 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
    ]"
    role="article"
  >
    <!-- Top Row: ID & Badges -->
    <div class="flex items-center justify-between gap-1 mb-1.5 text-xs font-mono min-w-0">
      <span class="text-slate-500 dark:text-slate-400 font-semibold truncate min-w-0" :title="task.id">{{ task.id }}</span>
      <div class="flex items-center gap-1.5 shrink-0">
        <span v-if="isCriticalPath && task.status !== 'DONE'" title="Critical Path" class="text-rose-600 dark:text-rose-400">
          <Flame class="w-3.5 h-3.5" />
        </span>
        <span class="h-5 px-1.5 inline-flex items-center justify-center rounded-md border text-[11px] uppercase font-bold" :class="getPriorityBadge(task.priority)">
          {{ task.priority.slice(0, 4) }}
        </span>
      </div>
    </div>


    <!-- Title -->
    <h4
      class="text-sm font-medium font-sans text-slate-900 dark:text-slate-100 mb-2 leading-snug"
      :class="task.status === 'DONE' ? 'line-through text-slate-400 dark:text-slate-500 font-normal' : ''"
    >
      {{ task.title }}
    </h4>

    <!-- Blocking Reason -->
    <div v-if="task.blockingReason && task.status === 'BLOCKED'" class="flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-400/90 font-mono mb-2 bg-rose-50 dark:bg-rose-950/30 p-1.5 rounded-md border border-rose-200 dark:border-rose-900/40">
      <AlertCircle class="w-3.5 h-3.5 shrink-0" />
      <span class="truncate">{{ task.blockingReason }}</span>
    </div>

    <!-- Footer Row: Due Date & Actions -->
    <div class="flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
      <div class="flex items-center gap-1">
        <Clock v-if="task.dueDate" class="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
        <span v-if="task.dueDate">{{ new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }}</span>
        <span v-else>-</span>
      </div>

      <!-- Quick Action Controls -->
      <div class="flex items-center gap-1.5 opacity-70 group-hover:opacity-100 transition-opacity">
        <!-- Edit Pencil Button -->
        <button
          type="button"
          @click="onEditClick"
          title="Edit details (Enter / i)"
          class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-indigo-600 dark:hover:text-indigo-400 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer"
        >
          <Pencil class="w-3.5 h-3.5" />
        </button>

        <!-- Status Chevrons < > -->
        <div class="flex items-center border border-slate-300 dark:border-slate-700 rounded-md overflow-hidden">
          <button
            type="button"
            @click="(e) => onStatusCycle(e, 'prev')"
            title="Previous status"
            class="px-1.5 py-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer"
          >
            ‹
          </button>
          <button
            type="button"
            @click="(e) => onStatusCycle(e, 'next')"
            title="Next status (Space)"
            class="px-1.5 py-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
