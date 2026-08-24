<script setup lang="ts">
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskStatus, TaskPriority } from '../types/task';
import { Flame, Plus, ChevronLeft, ChevronRight, Clock, AlertCircle } from 'lucide-vue-next';

defineProps<{
  onOpenCreate: () => void;
}>();

const taskStore = useTaskStore();

const COLUMNS: { status: TaskStatus; label: string; dotClass: string; borderClass: string; badgeClass: string }[] = [
  {
    status: 'TODO',
    label: 'To Do',
    dotClass: 'bg-slate-400 dark:bg-zinc-500',
    borderClass: 'border-slate-200 dark:border-zinc-800',
    badgeClass: 'text-slate-600 bg-slate-200/70 border-slate-300 dark:text-zinc-400 dark:bg-zinc-900 dark:border-zinc-800',
  },
  {
    status: 'IN_PROGRESS',
    label: 'In Progress',
    dotClass: 'bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.4)]',
    borderClass: 'border-sky-200 dark:border-sky-950/60',
    badgeClass: 'text-sky-700 bg-sky-100 border-sky-200 dark:text-sky-300 dark:bg-sky-950/40 dark:border-sky-800/60',
  },
  {
    status: 'BLOCKED',
    label: 'Blocked',
    dotClass: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]',
    borderClass: 'border-rose-200 dark:border-rose-950/60',
    badgeClass: 'text-rose-700 bg-rose-100 border-rose-200 dark:text-rose-300 dark:bg-rose-950/40 dark:border-rose-800/60',
  },
  {
    status: 'DONE',
    label: 'Completed',
    dotClass: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]',
    borderClass: 'border-emerald-200 dark:border-emerald-950/60',
    badgeClass: 'text-emerald-700 bg-emerald-100 border-emerald-200 dark:text-emerald-300 dark:bg-emerald-950/40 dark:border-emerald-800/60',
  },
];

function getPriorityBadge(p: TaskPriority) {
  switch (p) {
    case 'CRITICAL':
      return 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/80 font-bold';
    case 'HIGH':
      return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800/60 font-semibold';
    case 'MEDIUM':
      return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/40';
    case 'LOW':
    default:
      return 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-zinc-900 dark:text-zinc-400 dark:border-zinc-800';
  }
}

function moveStatus(task: Task, direction: 'left' | 'right') {
  const order: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];
  const currIdx = order.indexOf(task.status);
  if (direction === 'left' && currIdx > 0) {
    taskStore.setStatus(task.id, order[currIdx - 1]);
  } else if (direction === 'right' && currIdx < order.length - 1) {
    taskStore.setStatus(task.id, order[currIdx + 1]);
  }
}

function handleDragStart(e: DragEvent, taskId: string) {
  if (e.dataTransfer) {
    e.dataTransfer.setData('text/plain', taskId);
    e.dataTransfer.effectAllowed = 'move';
  }
}

function handleDragOver(e: DragEvent) {
  e.preventDefault();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move';
  }
}

function handleDrop(e: DragEvent, targetStatus: TaskStatus) {
  e.preventDefault();
  if (e.dataTransfer) {
    const taskId = e.dataTransfer.getData('text/plain');
    if (taskId) {
      taskStore.setStatus(taskId, targetStatus);
    }
  }
}
</script>

<template>
  <div class="w-full flex-1 p-3 md:p-4 overflow-x-auto">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3 md:gap-4 min-w-[300px] md:min-w-[900px] h-full items-start">
      <div
        v-for="col in COLUMNS"
        :key="col.status"
        class="flex flex-col bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-3 max-h-[calc(100vh-140px)] min-h-[300px]"
        @dragover="handleDragOver"
        @drop="(e) => handleDrop(e, col.status)"
        role="region"
        :aria-label="`${col.label} column`"
      >
        <!-- Column Header -->
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-slate-800/80 select-none">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" :class="col.dotClass"></span>
            <h3 class="text-xs font-mono font-bold text-slate-800 dark:text-zinc-200">{{ col.label }}</h3>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono border font-medium" :class="col.badgeClass">
            {{ taskStore.filteredTasks.filter((t) => t.status === col.status).length }}
          </span>
        </div>

        <!-- Cards List -->
        <div class="flex-1 overflow-y-auto space-y-2 pr-1 no-scrollbar">
          <div
            v-if="taskStore.filteredTasks.filter((t) => t.status === col.status).length === 0"
            class="text-center py-8 text-[11px] text-slate-400 dark:text-zinc-600 font-mono"
          >
            Empty column
          </div>

          <div
            v-for="task in taskStore.filteredTasks.filter((t) => t.status === col.status)"
            :key="task.id"
            class="group bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 border border-slate-200 dark:border-slate-700 rounded-lg p-2.5 transition shadow-xs cursor-grab active:cursor-grabbing select-none"
            draggable="true"
            @dragstart="(e) => handleDragStart(e, task.id)"
            role="article"
          >
            <!-- Top Row: ID & Badges -->
            <div class="flex items-center justify-between gap-1 mb-1.5 text-[10px] font-mono">
              <span class="text-slate-500 dark:text-zinc-400 font-medium">{{ task.id }}</span>
              <div class="flex items-center gap-1">
                <span v-if="taskStore.criticalPathIds.has(task.id) && task.status !== 'DONE'" title="Critical Path" class="text-rose-600 dark:text-rose-400">
                  <Flame class="w-3.5 h-3.5" />
                </span>
                <span class="px-1.5 py-0.2 rounded border" :class="getPriorityBadge(task.priority)">
                  {{ task.priority.slice(0, 4) }}
                </span>
              </div>
            </div>

            <!-- Title -->
            <h4 class="text-xs font-normal text-slate-800 dark:text-zinc-200 mb-1.5 leading-snug" :class="task.status === 'DONE' ? 'line-through text-slate-400 dark:text-zinc-500' : ''">
              {{ task.title }}
            </h4>

            <!-- Blocking Reason -->
            <div v-if="task.blockingReason && task.status === 'BLOCKED'" class="flex items-center gap-1 text-[10px] text-rose-700 dark:text-rose-400/90 font-mono mb-1.5 bg-rose-50 dark:bg-rose-950/30 p-1 rounded border border-rose-200 dark:border-rose-900/40">
              <AlertCircle class="w-3 h-3 shrink-0" />
              <span class="truncate">{{ task.blockingReason }}</span>
            </div>

            <!-- Footer Row -->
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-500 dark:text-zinc-400 pt-1.5 border-t border-slate-100 dark:border-slate-700/60">
              <div class="flex items-center gap-1">
                <Clock v-if="task.dueDate" class="w-3 h-3 text-slate-400 dark:text-zinc-500" />
                <span v-if="task.dueDate">{{ new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }}</span>
                <span v-else>-</span>
              </div>

              <!-- Quick Column Shift Controls -->
              <div class="flex items-center gap-0.5 opacity-60 group-hover:opacity-100 transition">
                <button
                  v-if="col.status !== 'TODO'"
                  type="button"
                  class="p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-200 cursor-pointer"
                  @click="moveStatus(task, 'left')"
                  title="Move left"
                >
                  <ChevronLeft class="w-3.5 h-3.5" />
                </button>
                <button
                  v-if="col.status !== 'DONE'"
                  type="button"
                  class="p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-200 cursor-pointer"
                  @click="moveStatus(task, 'right')"
                  title="Move right"
                >
                  <ChevronRight class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Column Quick Create Button -->
        <button
          type="button"
          class="w-full mt-2 py-1.5 rounded-lg border border-dashed border-slate-300 dark:border-zinc-800 hover:border-slate-400 dark:hover:border-zinc-700 hover:bg-white/60 dark:hover:bg-zinc-900/40 text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-200 text-xs font-mono flex items-center justify-center gap-1 cursor-pointer transition"
          @click="onOpenCreate"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Task</span>
        </button>
      </div>
    </div>
  </div>
</template>
