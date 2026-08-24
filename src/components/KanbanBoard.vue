<script setup lang="ts">
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskPriority, TaskStatus } from '../types/task';
import { Flame, Clock, Plus, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-vue-next';

defineProps<{
  onOpenCreate: () => void;
}>();

const taskStore = useTaskStore();

const COLUMNS: { status: TaskStatus; label: string; dotClass: string; borderClass: string; badgeClass: string }[] = [
  {
    status: 'TODO',
    label: 'To Do',
    dotClass: 'bg-slate-400 dark:bg-slate-500',
    borderClass: 'border-slate-300 dark:border-slate-800',
    badgeClass: 'text-slate-700 bg-slate-200 border-slate-300 dark:text-slate-400 dark:bg-slate-900 dark:border-slate-800',
  },
  {
    status: 'IN_PROGRESS',
    label: 'In Progress',
    dotClass: 'bg-sky-500',
    borderClass: 'border-sky-200 dark:border-sky-950/60',
    badgeClass: 'text-sky-700 bg-sky-100 border-sky-200 dark:text-sky-300 dark:bg-sky-950/40 dark:border-sky-800/60',
  },
  {
    status: 'BLOCKED',
    label: 'Blocked',
    dotClass: 'bg-rose-500',
    borderClass: 'border-rose-200 dark:border-rose-950/60',
    badgeClass: 'text-rose-700 bg-rose-100 border-rose-200 dark:text-rose-300 dark:bg-rose-950/40 dark:border-rose-800/60',
  },
  {
    status: 'DONE',
    label: 'Done',
    dotClass: 'bg-emerald-500',
    borderClass: 'border-emerald-200 dark:border-emerald-950/60',
    badgeClass: 'text-emerald-700 bg-emerald-100 border-emerald-200 dark:text-emerald-300 dark:bg-emerald-950/40 dark:border-emerald-800/60',
  },
];

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

function moveStatus(task: Task, direction: 'left' | 'right') {
  const statuses: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];
  const currentIndex = statuses.indexOf(task.status);
  const nextIndex = direction === 'left' ? currentIndex - 1 : currentIndex + 1;
  if (nextIndex >= 0 && nextIndex < statuses.length) {
    taskStore.setStatus(task.id, statuses[nextIndex]);
    taskStore.kanbanColIndex = nextIndex;
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

function handleDrop(e: DragEvent, targetStatus: TaskStatus, colIndex: number) {
  e.preventDefault();
  if (e.dataTransfer) {
    const taskId = e.dataTransfer.getData('text/plain');
    if (taskId) {
      taskStore.setStatus(taskId, targetStatus);
      taskStore.kanbanColIndex = colIndex;
    }
  }
}

function selectCard(task: Task, colIndex: number, rowIndex: number) {
  taskStore.kanbanColIndex = colIndex;
  taskStore.kanbanRowIndex = rowIndex;
}
</script>

<template>
  <div class="h-full grid grid-cols-1 md:grid-cols-4 gap-4 items-start">
    <div
      v-for="(col, colIndex) in COLUMNS"
      :key="col.status"
      class="flex flex-col h-full max-h-full bg-slate-200/60 dark:bg-slate-900/80 border rounded-lg p-3 shadow-2xs transition-colors"
      :class="taskStore.kanbanColIndex === colIndex ? 'border-slate-400 dark:border-slate-700' : 'border-slate-300 dark:border-slate-800'"
      @dragover="handleDragOver"
      @drop="(e) => handleDrop(e, col.status, colIndex)"
      role="region"
      :aria-label="`${col.label} column`"
    >
      <!-- Column Header -->
      <div class="shrink-0 pb-2.5 border-b border-slate-300 dark:border-slate-800 flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full" :class="col.dotClass"></span>
          <h3 class="text-xs md:text-sm font-mono font-bold text-slate-800 dark:text-slate-200">{{ col.label }}</h3>
        </div>
        <span class="h-6 px-2 inline-flex items-center justify-center rounded-md text-[11px] font-mono border font-semibold" :class="col.badgeClass">
          {{ taskStore.filteredTasks.filter((t) => t.status === col.status).length }}
        </span>
      </div>

      <!-- Cards Container (Clustered Naturally) -->
      <div class="flex-1 min-h-0 overflow-y-auto space-y-2.5 py-2.5 pr-1 no-scrollbar">
        <div
          v-if="taskStore.filteredTasks.filter((t) => t.status === col.status).length === 0"
          class="text-center py-6 text-xs text-slate-400 dark:text-slate-600 font-mono"
        >
          Empty column
        </div>

        <div
          v-for="(task, rowIndex) in taskStore.filteredTasks.filter((t) => t.status === col.status)"
          :key="task.id"
          class="group rounded-md p-3 shadow-xs cursor-grab active:cursor-grabbing select-none transition-colors border"
          :class="task.id === taskStore.activeKanbanTask?.id
            ? 'ring-2 ring-indigo-500 dark:ring-indigo-400 bg-indigo-50/80 dark:bg-slate-800 border-indigo-400 dark:border-slate-600'
            : 'bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 hover:border-slate-400 dark:hover:border-slate-700'"
          draggable="true"
          @dragstart="(e) => handleDragStart(e, task.id)"
          @click="selectCard(task, colIndex, rowIndex)"
          role="article"
        >
          <!-- Top Row: ID & Badges -->
          <div class="flex items-center justify-between gap-1 mb-1.5 text-xs font-mono">
            <span class="text-slate-500 dark:text-slate-400 font-semibold">{{ task.id }}</span>
            <div class="flex items-center gap-1.5">
              <span v-if="taskStore.criticalPathIds.has(task.id) && task.status !== 'DONE'" title="Critical Path" class="text-rose-600 dark:text-rose-400">
                <Flame class="w-3.5 h-3.5" />
              </span>
              <span class="h-5 px-1.5 inline-flex items-center justify-center rounded-md border text-[11px] uppercase font-bold" :class="getPriorityBadge(task.priority)">
                {{ task.priority.slice(0, 4) }}
              </span>
            </div>
          </div>

          <!-- Title -->
          <h4 class="text-sm font-medium font-sans text-slate-900 dark:text-slate-100 mb-2 leading-snug" :class="task.status === 'DONE' ? 'line-through text-slate-400 dark:text-slate-500 font-normal' : ''">
            {{ task.title }}
          </h4>

          <!-- Blocking Reason -->
          <div v-if="task.blockingReason && task.status === 'BLOCKED'" class="flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-400/90 font-mono mb-2 bg-rose-50 dark:bg-rose-950/30 p-1.5 rounded-md border border-rose-200 dark:border-rose-900/40">
            <AlertCircle class="w-3.5 h-3.5 shrink-0" />
            <span class="truncate">{{ task.blockingReason }}</span>
          </div>

          <!-- Footer Row -->
          <div class="flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div class="flex items-center gap-1">
              <Clock v-if="task.dueDate" class="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
              <span v-if="task.dueDate">{{ new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }}</span>
              <span v-else>-</span>
            </div>

            <!-- Quick Column Shift Controls -->
            <div class="flex items-center gap-1 opacity-60 group-hover:opacity-100 transition">
              <button
                v-if="col.status !== 'TODO'"
                type="button"
                class="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer"
                @click.stop="moveStatus(task, 'left')"
                title="Move left (H)"
              >
                <ChevronLeft class="w-3.5 h-3.5" />
              </button>
              <button
                v-if="col.status !== 'DONE'"
                type="button"
                class="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer"
                @click.stop="moveStatus(task, 'right')"
                title="Move right (L)"
              >
                <ChevronRight class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Add Button: h-8 rounded-md standard -->
      <button
        type="button"
        class="h-8 w-full mt-2 border border-dashed border-slate-300 dark:border-slate-700 rounded-md hover:bg-white dark:hover:bg-slate-800 text-xs font-mono transition flex items-center justify-center gap-1.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white cursor-pointer shrink-0"
        @click="onOpenCreate"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>New Task</span>
      </button>
    </div>
  </div>
</template>
