<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { api, type ProjectMember } from '../services/api';
import type { TaskPriority, TaskStatus } from '../types/task';
import { Plus, X, CalendarDays, UserPlus } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const title = ref('');
const priority = ref<TaskPriority>('MEDIUM');
const status = ref<TaskStatus>('TODO');
const dueDate = ref('');
const assigneeId = ref<number | ''>('');
const members = ref<ProjectMember[]>([]);
const inputRef = ref<HTMLInputElement | null>(null);

/**
 * Assigning work is a PM affordance. A member creating a task gets it in their
 * own queue; only a PM chooses somebody else's.
 *
 * This hides a control — it is not the boundary. The server refuses a
 * non-PM's attempt regardless (D6 P11).
 */
const canAssign = computed(() => taskStore.isProjectManager && members.value.length > 1);

/** Today, as the `min` for the date input — a deadline in the past is a typo. */
const today = new Date().toISOString().slice(0, 10);

function handleCreate() {
  if (!title.value.trim()) return;

  const chosen = assigneeId.value === '' ? null : Number(assigneeId.value);
  taskStore.createTask(title.value.trim(), priority.value, status.value, {
    // <input type="date"> gives YYYY-MM-DD with no time. Pin it to end of day
    // local: a task due "the 30th" is not late at 00:01 on the 30th.
    dueDate: dueDate.value ? new Date(`${dueDate.value}T23:59:59`).toISOString() : undefined,
    assigneeId: chosen,
    assignee: members.value.find((m) => m.user_id === chosen)?.full_name,
  });
  emit('close');
}

onMounted(async () => {
  inputRef.value?.focus();

  // Only a PM needs the roster, and only for a project that has one.
  if (taskStore.isProjectManager && taskStore.currentProjectId !== null) {
    try {
      const roster = await api.listMembers(taskStore.currentProjectId);
      // Pending invitations cannot be assigned work — they have no access to
      // the project yet and may never accept.
      members.value = roster.filter((m) => m.status === 'ACCEPTED');
    } catch (e) {
      console.warn('Could not load members for assignment:', e);
    }
  }
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-lg rounded-lg p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200">
            <Plus class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold text-slate-900 dark:text-slate-100 font-sans">Create New Task</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">High-velocity task authoring</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Form Body -->
      <form class="py-4 space-y-4 text-xs" @submit.prevent="handleCreate">
        <div>
          <label for="vue-create-task-title" class="block font-mono text-slate-700 dark:text-slate-300 mb-1.5 font-medium">Task Title *</label>
          <input
            id="vue-create-task-title"
            ref="inputRef"
            v-model="title"
            type="text"
            placeholder="e.g. Implement Vue 3 Composition API & Pinia Store..."
            required
            class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3.5 py-2.5 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 min-h-[44px]"
            @keydown.enter.prevent="handleCreate"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="vue-create-task-priority" class="block font-mono text-slate-600 dark:text-slate-400 mb-1.5 font-medium">Priority</label>
            <select
              id="vue-create-task-priority"
              v-model="priority"
              class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div>
            <label for="vue-create-task-status" class="block font-mono text-slate-600 dark:text-slate-400 mb-1.5 font-medium">Initial Status</label>
            <select
              id="vue-create-task-status"
              v-model="status"
              class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
            >
              <option value="TODO">TODO</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="BLOCKED">BLOCKED</option>
              <option value="DONE">DONE</option>
            </select>
          </div>
        </div>

        <div>
          <label for="vue-create-task-due" class="flex items-center gap-1.5 font-mono text-slate-600 dark:text-slate-400 mb-1.5 font-medium">
            <CalendarDays class="w-3.5 h-3.5" />
            <span>Due date</span>
          </label>
          <input
            id="vue-create-task-due"
            v-model="dueDate"
            type="date"
            :min="today"
            class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500 min-h-[40px]"
          />
          <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            Optional. Dated tasks sort to the top of the board as the deadline nears.
          </p>
        </div>

        <div v-if="canAssign">
          <label for="vue-create-task-assignee" class="flex items-center gap-1.5 font-mono text-slate-600 dark:text-slate-400 mb-1.5 font-medium">
            <UserPlus class="w-3.5 h-3.5" />
            <span>Assign to</span>
          </label>
          <select
            id="vue-create-task-assignee"
            v-model="assigneeId"
            class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500 min-h-[40px]"
          >
            <option value="">Unassigned</option>
            <option v-for="m in members" :key="m.user_id" :value="m.user_id">
              {{ m.full_name }} — {{ m.active_tasks_count }} active
            </option>
          </select>
          <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
            Current load is shown so you can spread work rather than stack it.
          </p>
        </div>

        <div class="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
          <button
            type="button"
            class="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 font-mono text-xs cursor-pointer min-h-[40px]"
            @click="emit('close')"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="px-5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-950 font-mono font-medium text-xs flex items-center gap-1.5 cursor-pointer shadow min-h-[40px]"
          >
            <Plus class="w-4 h-4 stroke-[2.5]" />
            <span>Create Task</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
