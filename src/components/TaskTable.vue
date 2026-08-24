<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskPriority, TaskStatus } from '../types/task';
import TaskContextMenu from './TaskContextMenu.vue';
import { Flame, Plus, Check, Edit3, Trash2 } from 'lucide-vue-next';

defineProps<{
  onOpenCreate: () => void;
}>();

const taskStore = useTaskStore();

// Context menu state
const contextMenu = ref<{ task: Task; x: number; y: number } | null>(null);

// Inline edit buffer
const editInputVal = ref('');
const editInputRef = ref<HTMLInputElement | null>(null);

// Swipe tracking for touch ergonomics
const pointerState = ref<{
  taskId: string | null;
  startX: number;
  startY: number;
  currentX: number;
  isSwiping: boolean;
}>({
  taskId: null,
  startX: 0,
  startY: 0,
  currentX: 0,
  isSwiping: false,
});

function getStatusDot(status: TaskStatus) {
  switch (status) {
    case 'DONE':
      return 'bg-emerald-600 dark:bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)]';
    case 'IN_PROGRESS':
      return 'bg-sky-600 dark:bg-sky-400 shadow-[0_0_8px_rgba(14,165,233,0.4)]';
    case 'BLOCKED':
      return 'bg-rose-600 dark:bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.4)]';
    case 'TODO':
    default:
      return 'bg-slate-500 dark:bg-zinc-500';
  }
}

function getStatusTextColor(status: TaskStatus) {
  switch (status) {
    case 'DONE':
      return 'text-emerald-700 dark:text-emerald-400';
    case 'IN_PROGRESS':
      return 'text-sky-700 dark:text-sky-300';
    case 'BLOCKED':
      return 'text-rose-700 dark:text-rose-300';
    case 'TODO':
    default:
      return 'text-slate-700 dark:text-zinc-400';
  }
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
      return 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-zinc-900 dark:text-zinc-400 dark:border-zinc-800 font-medium';
  }
}

function handlePointerDown(e: PointerEvent, task: Task) {
  if (e.button !== 0 && e.pointerType === 'mouse') return;
  pointerState.value = {
    taskId: task.id,
    startX: e.clientX,
    startY: e.clientY,
    currentX: e.clientX,
    isSwiping: false,
  };
}

function handlePointerMove(e: PointerEvent, task: Task) {
  if (pointerState.value.taskId !== task.id) return;
  const deltaX = e.clientX - pointerState.value.startX;
  const deltaY = Math.abs(e.clientY - pointerState.value.startY);

  if (Math.abs(deltaX) > 12 && deltaY < 24) {
    pointerState.value.isSwiping = true;
    pointerState.value.currentX = e.clientX;
  }
}

function handlePointerUp(e: PointerEvent, task: Task, idx: number) {
  if (pointerState.value.taskId === task.id) {
    const deltaX = pointerState.value.currentX - pointerState.value.startX;
    if (pointerState.value.isSwiping) {
      if (deltaX > 75) {
        taskStore.setStatus(task.id, 'DONE');
      } else if (deltaX < -75) {
        if (task.status === 'BLOCKED') {
          taskStore.deleteTask(task.id);
        } else {
          taskStore.setStatus(task.id, 'BLOCKED');
        }
      }
    } else {
      taskStore.selectTask(idx);
    }
  }
  pointerState.value = { taskId: null, startX: 0, startY: 0, currentX: 0, isSwiping: false };
}

function handlePointerCancel() {
  pointerState.value = { taskId: null, startX: 0, startY: 0, currentX: 0, isSwiping: false };
}

function handleContextMenu(e: MouseEvent, task: Task, idx: number) {
  e.preventDefault();
  taskStore.selectTask(idx);
  contextMenu.value = { task, x: e.clientX, y: e.clientY };
}

async function startInlineEdit(task: Task) {
  editInputVal.value = task.title;
  taskStore.startEditing(task.id);
  await nextTick();
  if (editInputRef.value) {
    editInputRef.value.focus();
    editInputRef.value.select();
  }
}

function commitInlineEdit(task: Task) {
  if (editInputVal.value.trim() && editInputVal.value !== task.title) {
    taskStore.updateTask(task.id, { title: editInputVal.value.trim() });
  }
  taskStore.stopEditing();
}

function handleEditKeydown(e: KeyboardEvent, task: Task) {
  if (e.key === 'Enter') {
    e.preventDefault();
    commitInlineEdit(task);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    taskStore.stopEditing();
  }
}

function cyclePriority(e: MouseEvent, taskId: string, current: TaskPriority) {
  e.stopPropagation();
  const priorities: TaskPriority[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
  const next = priorities[(priorities.indexOf(current) + 1) % priorities.length];
  taskStore.setPriority(taskId, next);
}
</script>

<template>
  <div class="relative w-full overflow-hidden flex flex-col bg-white dark:bg-slate-900">
    <!-- Desktop Table Header Bar -->
    <div class="hidden md:grid grid-cols-[70px_110px_1fr_80px_90px_90px_60px] items-center gap-3 px-3 py-2 text-[11px] font-mono font-semibold text-slate-700 dark:text-slate-400 border-b border-slate-300 dark:border-slate-800 bg-slate-100 dark:bg-slate-950/40 select-none">
      <span>ID</span>
      <span>Status</span>
      <span>Title</span>
      <span>Priority</span>
      <span>Complexity</span>
      <span>Due</span>
      <span class="text-right">Actions</span>
    </div>

    <!-- Empty State -->
    <div v-if="taskStore.filteredTasks.length === 0" class="flex flex-col items-center justify-center py-20 px-4 text-center">
      <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300">No tasks found</h3>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
        Press <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-400 font-mono text-[10px]">c</kbd> or tap Create Task.
      </p>
      <button
        type="button"
        class="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white dark:text-slate-200 text-xs font-mono cursor-pointer transition min-h-[36px]"
        @click="onOpenCreate"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>Create Task</span>
      </button>
    </div>

    <!-- Task List -->
    <div v-else class="divide-y divide-slate-200 dark:divide-slate-800/40 flex flex-col" role="list">
      <div
        v-for="(task, idx) in taskStore.filteredTasks"
        :key="task.id"
        class="group relative touch-card select-none h-[44px] md:h-[38px] flex items-center transition-colors duration-75"
        :class="idx === taskStore.selectedIndex ? 'bg-indigo-50 dark:bg-slate-800/80 border-l-2 border-indigo-600 dark:border-slate-400' : 'hover:bg-slate-50 dark:hover:bg-slate-800/60'"
        style="touch-action: pan-y;"
        @pointerdown="(e) => handlePointerDown(e, task)"
        @pointermove="(e) => handlePointerMove(e, task)"
        @pointerup="(e) => handlePointerUp(e, task, idx)"
        @pointercancel="handlePointerCancel"
        @contextmenu="(e) => handleContextMenu(e, task, idx)"
        role="listitem"
      >
        <!-- Desktop Row View (>= md) -->
        <div
          class="relative z-10 hidden md:grid grid-cols-[70px_110px_1fr_80px_90px_90px_60px] items-center gap-3 px-3 w-full h-full transition-transform duration-75"
          :class="task.status === 'DONE' ? 'opacity-50' : ''"
        >
          <!-- Col 1: ID & Critical Dot -->
          <div class="flex items-center gap-1.5 font-mono text-xs">
            <span class="text-slate-600 dark:text-slate-400 font-medium">{{ task.id }}</span>
            <span v-if="taskStore.criticalPathIds.has(task.id) && task.status !== 'DONE'" title="Critical Path" class="text-rose-600 dark:text-rose-400">
              <Flame class="w-3 h-3" />
            </span>
          </div>

          <!-- Col 2: Status -->
          <div class="flex items-center">
            <button
              type="button"
              class="inline-flex items-center gap-2 px-1.5 py-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800/60 text-xs font-mono cursor-pointer transition"
              :class="getStatusTextColor(task.status)"
              @click.stop="taskStore.cycleStatus(task.id)"
              title="Click or Space to cycle"
            >
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="getStatusDot(task.status)"></span>
              <span class="truncate font-semibold">{{ task.status }}</span>
            </button>
          </div>

          <!-- Col 3: Title -->
          <div class="flex items-center min-w-0 pr-2 overflow-hidden">
            <div v-if="taskStore.editingTaskId === task.id" class="flex items-center w-full" @click.stop>
              <input
                ref="editInputRef"
                v-model="editInputVal"
                type="text"
                class="w-full bg-white dark:bg-slate-950 border border-indigo-500 dark:border-slate-600 rounded px-2 py-0.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none font-sans shadow-xs"
                @keydown="(e) => handleEditKeydown(e, task)"
                @blur="commitInlineEdit(task)"
              />
            </div>
            <button
              v-else
              type="button"
              class="text-left w-full truncate text-xs font-medium text-slate-950 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-white cursor-text bg-transparent border-0 p-0 font-inherit block leading-none"
              @dblclick.stop="startInlineEdit(task)"
              title="Double click or Enter to edit"
            >
              <span class="truncate block" :class="task.status === 'DONE' ? 'line-through text-slate-400 dark:text-slate-600 font-normal' : ''">
                {{ task.title }}
              </span>
            </button>
          </div>

          <!-- Col 4: Priority -->
          <div class="flex items-center font-mono text-[11px]">
            <button
              type="button"
              class="px-1.5 py-0.5 rounded border text-[10px] font-mono cursor-pointer transition shadow-2xs"
              :class="getPriorityBadge(task.priority)"
              @click="(e) => cyclePriority(e, task.id, task.priority)"
              title="Click or 1-4 to change"
            >
              {{ task.priority }}
            </button>
          </div>

          <!-- Col 5: Complexity / Dep -->
          <div class="flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400 font-mono truncate">
            <span v-if="task.complexity" class="text-slate-800 dark:text-slate-300 font-semibold">[{{ task.complexity }}]</span>
            <span v-if="task.dependencies && task.dependencies.length > 0" class="text-slate-600 dark:text-slate-400 truncate" :title="`Deps: ${task.dependencies.join(', ')}`">
              ← {{ task.dependencies.join(', ') }}
            </span>
          </div>

          <!-- Col 6: Due Date -->
          <div class="flex items-center text-[11px] text-slate-600 dark:text-slate-400 font-mono truncate">
            <span v-if="task.dueDate">{{ new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }}</span>
            <span v-else>-</span>
          </div>

          <!-- Col 7: Actions -->
          <div class="flex items-center justify-end">
            <div class="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5">
              <button
                type="button"
                class="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 cursor-pointer"
                @click.stop="startInlineEdit(task)"
                title="Rename (Enter)"
              >
                <Edit3 class="w-3 h-3" />
              </button>
              <button
                type="button"
                class="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded text-slate-500 hover:text-rose-600 cursor-pointer"
                @click.stop="taskStore.deleteTask(task.id)"
                title="Delete (d)"
              >
                <Trash2 class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        <!-- Mobile Row View (< md) -->
        <div
          class="relative z-10 flex md:hidden items-center justify-between gap-2.5 px-3 w-full h-full"
          :class="task.status === 'DONE' ? 'opacity-50' : ''"
        >
          <!-- Left: Status Badge -->
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-1.5 py-1 rounded bg-slate-100 dark:bg-slate-900/60 border border-slate-300 dark:border-slate-800 text-[10px] font-mono cursor-pointer shrink-0"
            :class="getStatusTextColor(task.status)"
            @click.stop="taskStore.cycleStatus(task.id)"
          >
            <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="getStatusDot(task.status)"></span>
            <span class="font-semibold">{{ task.status === 'IN_PROGRESS' ? 'IN PROG' : task.status }}</span>
          </button>

          <!-- Center: Title -->
          <div class="flex-1 min-w-0 pr-1">
            <div v-if="taskStore.editingTaskId === task.id" class="flex items-center w-full" @click.stop>
              <input
                ref="editInputRef"
                v-model="editInputVal"
                type="text"
                class="w-full bg-white dark:bg-slate-950 border border-indigo-500 dark:border-slate-600 rounded px-2 py-0.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none font-sans shadow-xs"
                @keydown="(e) => handleEditKeydown(e, task)"
                @blur="commitInlineEdit(task)"
              />
            </div>
            <button
              v-else
              type="button"
              class="text-left w-full truncate text-xs font-medium text-slate-950 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-white cursor-text bg-transparent border-0 p-0 font-inherit block leading-none"
              @click="taskStore.selectTask(idx)"
              @dblclick.stop="startInlineEdit(task)"
            >
              <span class="truncate block" :class="task.status === 'DONE' ? 'line-through text-slate-400 dark:text-slate-600 font-normal' : ''">
                {{ task.title }}
              </span>
            </button>
          </div>

          <!-- Right: Priority & Critical Indicator -->
          <div class="flex items-center gap-1.5 shrink-0">
            <span v-if="taskStore.criticalPathIds.has(task.id) && task.status !== 'DONE'" title="Critical Path" class="text-rose-600 dark:text-rose-400">
              <Flame class="w-3.5 h-3.5" />
            </span>
            <button
              type="button"
              class="px-1.5 py-0.5 rounded border text-[9px] font-mono cursor-pointer shadow-2xs"
              :class="getPriorityBadge(task.priority)"
              @click="(e) => cyclePriority(e, task.id, task.priority)"
            >
              {{ task.priority.slice(0, 4) }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Context Menu -->
  <TaskContextMenu
    v-if="contextMenu"
    :task="contextMenu.task"
    :x="contextMenu.x"
    :y="contextMenu.y"
    @close="contextMenu = null"
  />
</template>
