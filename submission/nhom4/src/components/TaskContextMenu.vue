<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskPriority, TaskStatus } from '../types/task';
import { Check, Edit3, Trash2 } from 'lucide-vue-next';

const props = defineProps<{
  task: Task;
  x: number;
  y: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const positionStyle = computed(() => {
  const maxH = typeof window !== 'undefined' ? window.innerHeight : 800;
  const maxW = typeof window !== 'undefined' ? window.innerWidth : 1200;
  return {
    top: `${Math.min(props.y, maxH - 200)}px`,
    left: `${Math.min(props.x, maxW - 200)}px`,
  };
});

function handleStatus(s: TaskStatus) {
  taskStore.setStatus(props.task.id, s);
  emit('close');
}

function handlePriority(p: TaskPriority) {
  taskStore.setPriority(props.task.id, p);
  emit('close');
}

function handleEdit() {
  taskStore.startEditing(props.task.id);
  emit('close');
}

function handleDelete() {
  taskStore.deleteTask(props.task.id);
  emit('close');
}

function handleGlobalClick() {
  emit('close');
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick);
});

onUnmounted(() => {
  window.removeEventListener('click', handleGlobalClick);
});
</script>

<template>
  <div
    class="fixed z-50 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-1.5 shadow-2xl text-xs font-mono w-48 text-slate-800 dark:text-slate-200"
    :style="positionStyle"
    @click.stop
  >
    <div class="px-2 py-1 text-[11px] text-slate-400 dark:text-slate-500 font-bold border-b border-slate-100 dark:border-slate-900 mb-1">
      {{ task.id }}
    </div>

    <!-- Status Actions -->
    <button
      type="button"
      class="w-full text-left px-2 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-700 dark:text-slate-300 flex items-center gap-2 cursor-pointer"
      @click="handleStatus('DONE')"
    >
      <Check class="w-3.5 h-3.5 text-emerald-500" />
      <span>Mark DONE</span>
    </button>
    <button
      type="button"
      class="w-full text-left px-2 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-700 dark:text-slate-300 flex items-center gap-2 cursor-pointer"
      @click="handleStatus('IN_PROGRESS')"
    >
      <span class="w-2 h-2 rounded-full bg-sky-500"></span>
      <span>Set In Progress</span>
    </button>
    <button
      type="button"
      class="w-full text-left px-2 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-700 dark:text-slate-300 flex items-center gap-2 cursor-pointer"
      @click="handleStatus('BLOCKED')"
    >
      <span class="w-2 h-2 rounded-full bg-rose-500"></span>
      <span>Set Blocked</span>
    </button>

    <div class="my-1 border-t border-slate-100 dark:border-slate-900"></div>

    <!-- Edit / Rename -->
    <button
      type="button"
      class="w-full text-left px-2 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-700 dark:text-slate-300 flex items-center gap-2 cursor-pointer"
      @click="handleEdit"
    >
      <Edit3 class="w-3.5 h-3.5 text-slate-400 dark:text-slate-400" />
      <span>Rename Title</span>
    </button>

    <!-- Priority Submenu -->
    <div class="px-2 py-1 text-[11px] text-slate-400 dark:text-slate-500 font-bold border-t border-slate-100 dark:border-slate-900 mt-1">
      Priority:
    </div>
    <div class="grid grid-cols-4 gap-1 px-1 py-0.5">
      <button
        v-for="p in (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as TaskPriority[])"
        :key="p"
        type="button"
        class="text-[9px] py-0.5 rounded border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-900 text-center text-slate-700 dark:text-slate-300 cursor-pointer"
        @click="handlePriority(p)"
      >
        {{ p.slice(0, 3) }}
      </button>
    </div>

    <div class="my-1 border-t border-slate-100 dark:border-slate-900"></div>

    <!-- Delete -->
    <button
      type="button"
      class="w-full text-left px-2 py-1.5 rounded hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400 flex items-center gap-2 cursor-pointer"
      @click="handleDelete"
    >
      <Trash2 class="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
      <span>Delete Task</span>
    </button>
  </div>
</template>
