<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import type { TaskPriority, TaskStatus } from '../types/task';
import { Plus, X, Tag } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const title = ref('');
const priority = ref<TaskPriority>('MEDIUM');
const status = ref<TaskStatus>('TODO');
const inputRef = ref<HTMLInputElement | null>(null);

function handleCreate() {
  if (!title.value.trim()) return;
  taskStore.createTask(title.value.trim(), priority.value, status.value);
  emit('close');
}

onMounted(() => {
  if (inputRef.value) {
    inputRef.value.focus();
  }
});
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="glass-panel w-full max-w-lg rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-zinc-800 border border-zinc-700 text-zinc-200">
            <Plus class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">Create New Task</h2>
            <p class="text-[11px] text-zinc-400">High-velocity task authoring</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Form Body -->
      <form class="py-4 space-y-4 text-xs" @submit.prevent="handleCreate">
        <div>
          <label for="vue-create-task-title" class="block font-mono text-zinc-300 mb-1.5 font-medium">Task Title *</label>
          <input
            id="vue-create-task-title"
            ref="inputRef"
            v-model="title"
            type="text"
            placeholder="e.g. Implement Vue 3 Composition API & Pinia Store..."
            required
            class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 min-h-[44px]"
            @keydown.enter.prevent="handleCreate"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="vue-create-task-priority" class="block font-mono text-zinc-400 mb-1.5">Priority</label>
            <select
              id="vue-create-task-priority"
              v-model="priority"
              class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-indigo-500"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div>
            <label for="vue-create-task-status" class="block font-mono text-zinc-400 mb-1.5">Initial Status</label>
            <select
              id="vue-create-task-status"
              v-model="status"
              class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono focus:outline-none focus:border-indigo-500"
            >
              <option value="TODO">TODO</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="BLOCKED">BLOCKED</option>
              <option value="DONE">DONE</option>
            </select>
          </div>
        </div>

        <div class="pt-2 border-t border-zinc-800 flex items-center justify-end gap-2">
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 font-mono text-xs cursor-pointer transition min-h-[40px]"
            @click="emit('close')"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="px-5 py-2 rounded-xl bg-zinc-100 hover:bg-white text-zinc-950 font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer transition shadow min-h-[40px]"
          >
            <Plus class="w-4 h-4 stroke-[2.5]" />
            <span>Create Task</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
