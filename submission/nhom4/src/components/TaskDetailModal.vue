<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskPriority, TaskStatus, Complexity } from '../types/task';
import {
  X,
  AlertCircle,
  Flame,
  Layers,
  ChevronDown,
} from 'lucide-vue-next';

const props = defineProps<{
  taskId: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();
const isEditing = ref(false);
const titleInputRef = ref<HTMLInputElement | null>(null);

const task = computed<Task | null>(() => {
  return taskStore.tasks.find((t) => t.id === props.taskId) || null;
});

const formattedDate = computed(() => {
  if (!task.value) return '';
  return new Date(task.value.createdAt).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
});

// Full-field edit reactive buffers
const editTitle = ref('');
const editStatus = ref<TaskStatus>('TODO');
const editPriority = ref<TaskPriority>('MEDIUM');
const editComplexity = ref<Complexity>('M');
const editAssignee = ref<string>('');
const editDueDate = ref<string>('');
const editDescription = ref('');
const editBlockingReason = ref('');

function initBuffers() {
  if (task.value) {
    editTitle.value = task.value.title;
    editStatus.value = task.value.status;
    editPriority.value = task.value.priority;
    editComplexity.value = (task.value.complexity as Complexity) || 'M';
    editAssignee.value = task.value.assignee || '';
    editDueDate.value = task.value.dueDate ? task.value.dueDate.slice(0, 10) : '';
    editDescription.value = task.value.description || '';
    editBlockingReason.value = task.value.blockingReason || '';
  }
}

watch(
  () => props.taskId,
  () => {
    isEditing.value = false;
    initBuffers();
  },
  { immediate: true }
);

async function enterEditMode() {
  initBuffers();
  isEditing.value = true;
  await nextTick();
  if (titleInputRef.value) {
    titleInputRef.value.focus();
    titleInputRef.value.select();
  }
}

function saveAndExit() {
  if (!task.value) return;
  if (editTitle.value.trim()) {
    taskStore.updateTask(task.value.id, {
      title: editTitle.value.trim(),
      status: editStatus.value,
      priority: editPriority.value,
      complexity: editComplexity.value,
      assignee: editAssignee.value.trim() || undefined,
      dueDate: editDueDate.value ? new Date(editDueDate.value).toISOString() : undefined,
      description: editDescription.value.trim() || undefined,
      blockingReason: editStatus.value === 'BLOCKED' ? editBlockingReason.value.trim() || undefined : undefined,
    });
  }
  isEditing.value = false;
}

// Live auto-save on field changes while editing
function onFieldChange() {
  if (isEditing.value && task.value) {
    taskStore.updateTask(task.value.id, {
      title: editTitle.value.trim() || task.value.title,
      status: editStatus.value,
      priority: editPriority.value,
      complexity: editComplexity.value,
      assignee: editAssignee.value.trim() || undefined,
      dueDate: editDueDate.value ? new Date(editDueDate.value).toISOString() : undefined,
      description: editDescription.value.trim() || undefined,
      blockingReason: editStatus.value === 'BLOCKED' ? editBlockingReason.value.trim() || undefined : undefined,
    });
  }
}

function handleKeydown(e: KeyboardEvent) {
  // If in View mode and user presses 'i': Enter edit mode
  if (!isEditing.value && e.key === 'i') {
    e.preventDefault();
    e.stopPropagation();
    enterEditMode();
    return;
  }

  // If in Edit mode and user presses 'Escape': Save changes and exit edit mode
  if (isEditing.value && e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    saveAndExit();
    return;
  }

  // If in View mode and user presses 'Escape': Close inspector dialog
  if (!isEditing.value && e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    emit('close');
    return;
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown, true);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown, true);
});

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

function getStatusBadge(s: TaskStatus) {
  switch (s) {
    case 'DONE':
      return 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800/60';
    case 'IN_PROGRESS':
      return 'bg-sky-100 text-sky-800 border-sky-300 dark:bg-sky-950/50 dark:text-sky-300 dark:border-sky-800/60';
    case 'BLOCKED':
      return 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800/60';
    case 'TODO':
    default:
      return 'bg-slate-200 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700';
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6"
    @click.self="emit('close')"
  >
    <div
      v-if="task"
      class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-lg shadow-2xl border border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[90vh] overflow-hidden focus:outline-none"
    >
      <!-- Modal Header (Single Close Button) -->
      <div class="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between select-none bg-slate-50/50 dark:bg-slate-950/40 shrink-0 gap-3">
        <!-- Left Badge Group -->
        <div class="flex items-center gap-2 shrink-0 flex-wrap sm:flex-nowrap">
          <span class="h-6 px-2.5 inline-flex items-center justify-center rounded-md font-mono text-[11px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 whitespace-nowrap shrink-0">
            {{ task.id }}
          </span>

          <!-- Status Selector / Chip -->
          <div v-if="isEditing" class="relative inline-block">
            <select
              v-model="editStatus"
              class="h-6 pl-2 pr-6 appearance-none rounded-md font-mono text-[11px] font-bold uppercase tracking-wider border bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none cursor-pointer"
              :class="getStatusBadge(editStatus)"
              @change="onFieldChange"
            >
              <option value="TODO">TODO</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="BLOCKED">BLOCKED</option>
              <option value="DONE">DONE</option>
            </select>
            <ChevronDown class="w-3 h-3 absolute right-1.5 top-1.5 pointer-events-none opacity-60" />
          </div>
          <span
            v-else
            class="h-6 px-2.5 inline-flex items-center justify-center rounded-md font-mono text-[11px] font-bold uppercase tracking-wider whitespace-nowrap shrink-0 border"
            :class="getStatusBadge(task.status)"
          >
            {{ task.status }}
          </span>

          <span
            v-if="taskStore.criticalPathIds.has(task.id) && task.status !== 'DONE'"
            title="Critical Path"
            class="h-6 px-2.5 inline-flex items-center gap-1.5 rounded-md font-mono text-[11px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 whitespace-nowrap shrink-0"
          >
            <Flame class="w-3.5 h-3.5 shrink-0" />
            <span>CRITICAL PATH</span>
          </span>
        </div>

        <!-- Right: Single Close Button -->
        <button
          type="button"
          class="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer shrink-0"
          @click="emit('close')"
          title="Close (Esc)"
        >
          <X class="w-5 h-5 shrink-0" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-5 md:p-6 overflow-y-auto space-y-5 flex-1 text-xs md:text-sm font-sans">
        <!-- Title Field (Interactive / Editable) -->
        <div>
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
            Title
          </label>
          <div v-if="!isEditing">
            <h3
              class="text-base md:text-lg font-semibold text-slate-950 dark:text-slate-50 leading-snug hover:bg-slate-100 dark:hover:bg-slate-800/60 p-1 -m-1 rounded cursor-text"
              @click="enterEditMode"
              title="Click to edit"
            >
              {{ task.title }}
            </h3>
          </div>
          <div v-else>
            <input
              ref="titleInputRef"
              v-model="editTitle"
              type="text"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-indigo-500 rounded-md px-3 py-1.5 text-base font-semibold font-sans text-slate-950 dark:text-slate-50 focus:outline-none shadow-xs"
              placeholder="Task Title..."
              @input="onFieldChange"
            />
          </div>
        </div>

        <!-- Meta Grid (4 Interactive Pickers) -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 dark:bg-slate-950/60 rounded-lg border border-slate-200 dark:border-slate-800/80">
          <!-- Priority Selector -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Priority</span>
            <div v-if="!isEditing">
              <span class="h-6 px-2 inline-flex items-center justify-center rounded-md border text-[11px] font-mono font-semibold uppercase" :class="getPriorityBadge(task.priority)">
                {{ task.priority }}
              </span>
            </div>
            <div v-else class="relative">
              <select
                v-model="editPriority"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-2 pr-6 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none appearance-none cursor-pointer font-semibold"
                :class="getPriorityBadge(editPriority)"
                @change="onFieldChange"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
              <ChevronDown class="w-3 h-3 absolute right-1.5 top-2 pointer-events-none opacity-60" />
            </div>
          </div>

          <!-- Complexity Selector -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Complexity</span>
            <div v-if="!isEditing">
              <span class="font-mono text-xs font-bold text-slate-800 dark:text-slate-200">
                {{ task.complexity || 'M' }} ({{ task.complexity === 'S' ? '1pt' : task.complexity === 'M' ? '2pts' : task.complexity === 'L' ? '3pts' : '5pts' }})
              </span>
            </div>
            <div v-else class="relative">
              <select
                v-model="editComplexity"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-2 pr-6 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none appearance-none cursor-pointer"
                @change="onFieldChange"
              >
                <option value="S">S (1pt)</option>
                <option value="M">M (2pts)</option>
                <option value="L">L (3pts)</option>
                <option value="XL">XL (5pts)</option>
              </select>
              <ChevronDown class="w-3 h-3 absolute right-1.5 top-2 pointer-events-none opacity-60" />
            </div>
          </div>

          <!-- Assignee Selector -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Assignee</span>
            <div v-if="!isEditing" class="flex items-center gap-1.5 text-xs font-mono text-slate-700 dark:text-slate-300 truncate">
              <span>{{ task.assignee || 'Unassigned' }}</span>
            </div>
            <div v-else class="relative">
              <select
                v-model="editAssignee"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-2 pr-6 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none appearance-none cursor-pointer"
                @change="onFieldChange"
              >
                <option value="">Unassigned</option>
                <option value="tupm">Phạm Minh Tú (PM)</option>
                <option value="dev">Dev Member</option>
                <option value="huynh">Phạm Văn Huynh</option>
                <option value="don">Đàm Đức Đôn</option>
              </select>
              <ChevronDown class="w-3 h-3 absolute right-1.5 top-2 pointer-events-none opacity-60" />
            </div>
          </div>

          <!-- Due Date Picker -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Due Date</span>
            <div v-if="!isEditing" class="flex items-center gap-1.5 text-xs font-mono text-slate-700 dark:text-slate-300">
              <span>{{ task.dueDate ? new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'None' }}</span>
            </div>
            <div v-else>
              <input
                v-model="editDueDate"
                type="date"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-1.5 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none"
                @change="onFieldChange"
              />
            </div>
          </div>
        </div>

        <!-- Blocking Reason (When Blocked) -->
        <div v-if="editStatus === 'BLOCKED' || task.status === 'BLOCKED' || editBlockingReason" class="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 rounded-lg">
          <div class="flex items-center gap-1.5 text-rose-800 dark:text-rose-300 text-xs font-mono font-semibold mb-1">
            <AlertCircle class="w-4 h-4 shrink-0" />
            <span>BLOCKING REASON</span>
          </div>
          <p v-if="!isEditing" class="text-xs font-sans text-rose-900 dark:text-rose-200">
            {{ task.blockingReason || 'No blocking reason specified.' }}
          </p>
          <input
            v-else
            v-model="editBlockingReason"
            type="text"
            class="w-full h-8 bg-white dark:bg-slate-900 border border-rose-300 dark:border-rose-800 rounded-md px-2.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none"
            placeholder="Describe what is blocking this task..."
            @input="onFieldChange"
          />
        </div>

        <!-- Description Field -->
        <div>
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
            Description
          </label>

          <!-- View Mode -->
          <div
            v-if="!isEditing"
            class="p-3.5 bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80 rounded-lg min-h-[90px] cursor-text hover:border-slate-300 dark:hover:border-slate-700"
            @click="enterEditMode"
            title="Click to edit"
          >
            <p v-if="task.description" class="text-xs md:text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
              {{ task.description }}
            </p>
            <span v-else class="text-xs text-slate-400 dark:text-slate-600 italic">
              No description provided. Click to add details.
            </span>
          </div>

          <!-- Edit Mode (Auto-growing textarea) -->
          <div v-else>
            <textarea
              v-model="editDescription"
              rows="5"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 focus:border-indigo-500 rounded-md p-3 text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none font-sans shadow-xs leading-relaxed"
              placeholder="Add a more detailed description..."
              @input="onFieldChange"
            ></textarea>
          </div>
        </div>

        <!-- Dependencies -->
        <div v-if="task.dependencies && task.dependencies.length > 0">
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
            Prerequisites & Dependencies
          </label>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="depId in task.dependencies"
              :key="depId"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-700 dark:text-slate-300 font-semibold"
            >
              <Layers class="w-3 h-3 text-slate-400 shrink-0" />
              <span>{{ depId }}</span>
            </span>
          </div>
        </div>

        <!-- Acceptance Criteria -->
        <div v-if="task.acceptanceCriteria && task.acceptanceCriteria.length > 0">
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
            Acceptance Criteria
          </label>
          <div class="space-y-1.5">
            <div
              v-for="(crit, idx) in task.acceptanceCriteria"
              :key="idx"
              class="flex items-center justify-between p-2 rounded bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80"
            >
              <div class="flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0"></span>
                <span class="text-xs text-slate-800 dark:text-slate-200">{{ crit }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer Action Strip (Single Done Action) -->
      <div class="px-5 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex items-center justify-between text-xs select-none shrink-0">
        <!-- Left: Metadata -->
        <span class="font-mono text-[11px] text-slate-500 dark:text-slate-400">
          {{ isEditing ? 'Auto-saves on exit' : `Created: ${formattedDate}` }}
        </span>

        <!-- Right: Actions & Keycaps -->
        <div class="flex items-center gap-2 font-mono">
          <!-- View Mode Keycaps -->
          <template v-if="!isEditing">
            <span class="text-slate-600 dark:text-slate-400">
              <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px]">i</kbd> Edit
            </span>
            <span class="text-slate-600 dark:text-slate-400">
              <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px]">Esc</kbd> Close
            </span>
          </template>

          <!-- Edit Mode Actions & Keycaps -->
          <template v-else>
            <span class="text-slate-600 dark:text-slate-400 mr-1">
              <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px]">Esc</kbd> Done
            </span>
            <button
              type="button"
              class="h-7 px-3 rounded-md bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 font-sans font-medium text-xs cursor-pointer shadow-xs"
              @click="saveAndExit"
            >
              Done
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
