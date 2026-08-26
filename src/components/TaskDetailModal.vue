<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import type { Task, TaskPriority, TaskStatus, Complexity } from '../types/task';
import {
  X,
  Edit2,
  Check,
  Clock,
  User,
  AlertCircle,
  Flame,
  Tag,
  ListTodo,
  Calendar,
  Layers,
  Sparkles,
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

// Edit Buffers
const editTitle = ref('');
const editDescription = ref('');
const editPriority = ref<TaskPriority>('MEDIUM');
const editComplexity = ref<Complexity>('M');
const editAssignee = ref('');
const editDueDate = ref('');
const editBlockingReason = ref('');
const newCriteria = ref('');

function initBuffers() {
  if (task.value) {
    editTitle.value = task.value.title;
    editDescription.value = task.value.description || '';
    editPriority.value = task.value.priority;
    editComplexity.value = task.value.complexity || 'M';
    editAssignee.value = task.value.assignee || '';
    editDueDate.value = task.value.dueDate ? task.value.dueDate.split('T')[0] : '';
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
      description: editDescription.value.trim() || undefined,
      priority: editPriority.value,
      complexity: editComplexity.value,
      assignee: editAssignee.value.trim() || undefined,
      dueDate: editDueDate.value ? new Date(editDueDate.value).toISOString() : undefined,
      blockingReason: task.value.status === 'BLOCKED' ? editBlockingReason.value.trim() || undefined : undefined,
    });
  }
  isEditing.value = false;
}

function handleKeydown(e: KeyboardEvent) {
  // If in View mode and user presses 'i'
  if (!isEditing.value && e.key === 'i') {
    e.preventDefault();
    e.stopPropagation();
    enterEditMode();
    return;
  }

  // If in Edit mode and user presses 'Escape'
  if (isEditing.value && e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    saveAndExit();
    return;
  }

  // If in View mode and user presses 'Escape'
  if (!isEditing.value && e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    emit('close');
    return;
  }
}

function toggleAcceptanceCriteria(idx: number) {
  if (!task.value) return;
  const list = [...(task.value.acceptanceCriteria || [])];
  // Toggle strike-through / completed state prefix if any, or remove
  // For simplicity, persist criteria in array
  taskStore.updateTask(task.value.id, { acceptanceCriteria: list });
}

function addCriteria() {
  if (!task.value || !newCriteria.value.trim()) return;
  const list = [...(task.value.acceptanceCriteria || []), newCriteria.value.trim()];
  taskStore.updateTask(task.value.id, { acceptanceCriteria: list });
  newCriteria.value = '';
}

function removeCriteria(idx: number) {
  if (!task.value) return;
  const list = (task.value.acceptanceCriteria || []).filter((_, i) => i !== idx);
  taskStore.updateTask(task.value.id, { acceptanceCriteria: list });
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
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100"
    @click.self="emit('close')"
    @keydown="handleKeydown"
    tabindex="-1"
  >
    <div
      v-if="task"
      class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-lg shadow-2xl border border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[90vh] overflow-hidden"
    >
      <!-- Modal Header -->
      <div class="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between select-none bg-slate-50/50 dark:bg-slate-950/40 shrink-0">
        <div class="flex items-center gap-2.5">
          <span class="font-mono text-xs font-bold text-slate-600 dark:text-slate-400 bg-slate-200/80 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700">
            {{ task.id }}
          </span>

          <span class="h-6 px-2 inline-flex items-center justify-center rounded-md border text-[11px] font-mono font-semibold uppercase tracking-wider" :class="getStatusBadge(task.status)">
            {{ task.status }}
          </span>

          <span v-if="taskStore.criticalPathIds.has(task.id) && task.status !== 'DONE'" title="Critical Path" class="flex items-center gap-1 text-rose-600 dark:text-rose-400 text-xs font-mono font-bold bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded border border-rose-200 dark:border-rose-900/40">
            <Flame class="w-3.5 h-3.5" />
            <span>CRITICAL PATH</span>
          </span>
        </div>

        <div class="flex items-center gap-2">
          <!-- State Indicator Tag -->
          <span
            class="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded border"
            :class="isEditing
              ? 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60 font-semibold animate-pulse'
              : 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'"
          >
            {{ isEditing ? 'EDIT MODE (Esc to Save)' : 'VIEW MODE (Press i to Edit)' }}
          </span>

          <button
            v-if="!isEditing"
            type="button"
            class="h-7 px-2.5 inline-flex items-center gap-1.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-sans font-medium transition cursor-pointer border border-slate-200 dark:border-slate-700"
            @click="enterEditMode"
            title="Edit task (i)"
          >
            <Edit2 class="w-3.5 h-3.5" />
            <span>Edit</span>
          </button>

          <button
            v-else
            type="button"
            class="h-7 px-2.5 inline-flex items-center gap-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-sans font-medium transition cursor-pointer shadow-2xs"
            @click="saveAndExit"
            title="Save and Exit (Esc)"
          >
            <Check class="w-3.5 h-3.5" />
            <span>Done</span>
          </button>

          <button
            type="button"
            class="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
            @click="emit('close')"
            title="Close dialog (Esc)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Modal Body -->
      <div class="p-5 md:p-6 overflow-y-auto space-y-5 flex-1 text-xs md:text-sm font-sans">
        <!-- Title Area -->
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 uppercase font-mono tracking-wider">
            Title
          </label>
          <div v-if="!isEditing">
            <h3 class="text-base md:text-lg font-semibold text-slate-950 dark:text-slate-50 leading-snug">
              {{ task.title }}
            </h3>
          </div>
          <div v-else>
            <input
              ref="titleInputRef"
              v-model="editTitle"
              type="text"
              class="w-full h-9 bg-white dark:bg-slate-950 border border-indigo-500 dark:border-slate-600 rounded-md px-3 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans shadow-xs font-medium"
              placeholder="Task Title..."
            />
          </div>
        </div>

        <!-- Meta Grid: Priority, Complexity, Assignee, Due Date -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 dark:bg-slate-950/60 rounded-lg border border-slate-200 dark:border-slate-800/80">
          <!-- Priority -->
          <div>
            <span class="block text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400 mb-1">Priority</span>
            <div v-if="!isEditing">
              <span class="h-6 px-2 inline-flex items-center justify-center rounded-md border text-[11px] font-mono font-semibold uppercase" :class="getPriorityBadge(task.priority)">
                {{ task.priority }}
              </span>
            </div>
            <div v-else>
              <select
                v-model="editPriority"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>
          </div>

          <!-- Complexity -->
          <div>
            <span class="block text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400 mb-1">Complexity</span>
            <div v-if="!isEditing">
              <span class="font-mono text-xs font-bold text-slate-800 dark:text-slate-200">
                {{ task.complexity || 'M' }} ({{ task.complexity === 'S' ? '1pt' : task.complexity === 'M' ? '2pts' : task.complexity === 'L' ? '3pts' : '5pts' }})
              </span>
            </div>
            <div v-else>
              <select
                v-model="editComplexity"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none"
              >
                <option value="S">S (1pt)</option>
                <option value="M">M (2pts)</option>
                <option value="L">L (3pts)</option>
                <option value="XL">XL (5pts)</option>
              </select>
            </div>
          </div>

          <!-- Assignee -->
          <div>
            <span class="block text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400 mb-1">Assignee</span>
            <div v-if="!isEditing" class="flex items-center gap-1.5 text-xs font-mono text-slate-700 dark:text-slate-300">
              <User class="w-3.5 h-3.5 text-slate-400" />
              <span>{{ task.assignee || 'Unassigned' }}</span>
            </div>
            <div v-else>
              <input
                v-model="editAssignee"
                type="text"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none"
                placeholder="Assignee..."
              />
            </div>
          </div>

          <!-- Due Date -->
          <div>
            <span class="block text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400 mb-1">Due Date</span>
            <div v-if="!isEditing" class="flex items-center gap-1.5 text-xs font-mono text-slate-700 dark:text-slate-300">
              <Calendar class="w-3.5 h-3.5 text-slate-400" />
              <span>{{ task.dueDate ? new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'None' }}</span>
            </div>
            <div v-else>
              <input
                v-model="editDueDate"
                type="date"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-1.5 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none"
              />
            </div>
          </div>
        </div>

        <!-- Blocking Reason (When Blocked) -->
        <div v-if="task.status === 'BLOCKED' || (isEditing && editBlockingReason)" class="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 rounded-lg">
          <div class="flex items-center gap-1.5 text-rose-800 dark:text-rose-300 text-xs font-mono font-semibold mb-1">
            <AlertCircle class="w-4 h-4" />
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
          />
        </div>

        <!-- Description -->
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 uppercase font-mono tracking-wider">
            Description
          </label>
          <div v-if="!isEditing" class="p-3 bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80 rounded-lg min-h-[70px]">
            <p v-if="task.description" class="text-xs md:text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
              {{ task.description }}
            </p>
            <span v-else class="text-xs text-slate-400 dark:text-slate-600 italic">No description provided.</span>
          </div>
          <div v-else>
            <textarea
              v-model="editDescription"
              rows="4"
              class="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md p-3 text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-sans shadow-xs leading-relaxed"
              placeholder="Task details and technical specifications..."
            ></textarea>
          </div>
        </div>

        <!-- Dependencies -->
        <div v-if="task.dependencies && task.dependencies.length > 0">
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 uppercase font-mono tracking-wider">
            Prerequisites & Dependencies
          </label>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="depId in task.dependencies"
              :key="depId"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-700 dark:text-slate-300 font-semibold"
            >
              <Layers class="w-3 h-3 text-slate-400" />
              <span>{{ depId }}</span>
            </span>
          </div>
        </div>

        <!-- Acceptance Criteria -->
        <div>
          <label class="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 uppercase font-mono tracking-wider">
            Acceptance Criteria
          </label>
          <div class="space-y-1.5">
            <div
              v-for="(crit, idx) in task.acceptanceCriteria || []"
              :key="idx"
              class="flex items-center justify-between p-2 rounded bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80 group"
            >
              <div class="flex items-center gap-2">
                <input
                  type="checkbox"
                  class="rounded text-indigo-600 focus:ring-0 cursor-pointer"
                  @change="toggleAcceptanceCriteria(idx)"
                />
                <span class="text-xs text-slate-800 dark:text-slate-200">{{ crit }}</span>
              </div>
              <button
                v-if="isEditing"
                type="button"
                class="opacity-0 group-hover:opacity-100 text-rose-500 hover:text-rose-700 text-xs p-0.5 cursor-pointer"
                @click="removeCriteria(idx)"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Add criteria input in edit mode -->
            <div v-if="isEditing" class="flex items-center gap-2 mt-2">
              <input
                v-model="newCriteria"
                type="text"
                class="flex-1 h-7 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md px-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none"
                placeholder="Add acceptance criterion..."
                @keydown.enter.prevent="addCriteria"
              />
              <button
                type="button"
                class="h-7 px-2.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 rounded-md text-xs font-mono font-medium cursor-pointer"
                @click="addCriteria"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-5 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex items-center justify-between text-xs font-mono text-slate-500 dark:text-slate-400 shrink-0">
        <div>
          <span>Created: {{ new Date(task.createdAt).toLocaleDateString() }}</span>
        </div>
        <div class="flex items-center gap-2">
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300">i</kbd> Edit</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300">Esc</kbd> Close</span>
        </div>
      </div>
    </div>
  </div>
</template>
