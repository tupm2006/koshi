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
  FileText,
  Trash2,
  Plus,
} from 'lucide-vue-next';

const props = defineProps<{
  taskId: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();
const isEditing = ref(false);

const userRole = computed<'OWNER' | 'PM' | 'MEMBER' | 'VIEWER'>(() => {
  return (taskStore.currentUser?.role as any) || 'PM';
});
const isMember = computed(() => userRole.value === 'MEMBER');
const isPmOrOwner = computed(() => !taskStore.currentUser || userRole.value === 'PM' || userRole.value === 'OWNER');

// Priority Governance State (Member Proposal)
const isProposingPriority = ref(false);
const proposedPriority = ref<TaskPriority>('HIGH');
const proposedReason = ref('');

function openProposePriority() {
  if (task.value) {
    proposedPriority.value = (task.value.requestedPriority || (task.value.priority === 'CRITICAL' ? 'HIGH' : 'CRITICAL')) as TaskPriority;
    proposedReason.value = task.value.priorityRequestReason || '';
  }
  isProposingPriority.value = true;
}

function submitPriorityProposal() {
  if (!task.value) return;
  taskStore.requestPriorityChange(task.value.id, proposedPriority.value, proposedReason.value.trim());
  isProposingPriority.value = false;
}

// Document Management State
const newDocUrl = ref('');

function addDocument() {
  const url = newDocUrl.value.trim();
  if (!url || !task.value) return;
  const currentDocs = task.value.documents ? [...task.value.documents] : [];
  if (!currentDocs.includes(url)) {
    currentDocs.push(url);
    taskStore.updateTask(task.value.id, { documents: currentDocs });
  }
  newDocUrl.value = '';
}

function removeDocument(index: number) {
  if (!task.value || !task.value.documents) return;
  const currentDocs = [...task.value.documents];
  currentDocs.splice(index, 1);
  taskStore.updateTask(task.value.id, { documents: currentDocs });
}

// Focus Refs for Sequential Tab Focus Traversal
const titleInput = ref<HTMLInputElement | null>(null);
const statusSelect = ref<HTMLSelectElement | null>(null);
const prioritySelect = ref<HTMLSelectElement | null>(null);
const complexitySelect = ref<HTMLSelectElement | null>(null);
const assigneeSelect = ref<HTMLSelectElement | null>(null);
const dueDateInput = ref<HTMLInputElement | null>(null);
const descriptionInput = ref<HTMLTextAreaElement | null>(null);

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

watch(
  isEditing,
  async (newVal) => {
    if (newVal) {
      await nextTick();
      titleInput.value?.focus();
      titleInput.value?.select();
    }
  }
);

async function enterEditMode() {
  initBuffers();
  isEditing.value = true;
  await nextTick();
  titleInput.value?.focus();
  titleInput.value?.select();
}

function saveAndExit() {
  if (!task.value) return;
  if (editTitle.value.trim()) {
    taskStore.updateTask(task.value.id, {
      title: editTitle.value.trim(),
      status: editStatus.value,
      priority: isMember.value ? task.value.priority : editPriority.value,
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
      priority: isMember.value ? task.value.priority : editPriority.value,
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
  // Allow native Tab, Shift+Tab, and Arrow keys focus traversal through all inputs
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
      <!-- Modal Header (Single Close Button, No Duplicate Save) -->
      <div class="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between select-none bg-slate-50/50 dark:bg-slate-950/40 shrink-0 gap-3">
        <!-- Left Badge Group -->
        <div class="flex items-center gap-2 shrink-0 flex-wrap sm:flex-nowrap">
          <span class="h-6 px-2.5 inline-flex items-center justify-center rounded-md font-mono text-[11px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 whitespace-nowrap shrink-0">
            {{ task.id }}
          </span>

          <!-- Status Selector / Chip -->
          <div v-if="isEditing" class="relative inline-block">
            <select
              ref="statusSelect"
              tabindex="2"
              v-model="editStatus"
              class="h-6 pl-2 pr-6 appearance-none rounded-md font-mono text-[11px] font-bold uppercase tracking-wider border bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
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
            <span>🔥 CRITICAL PATH</span>
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
        <!-- PM/OWNER: Priority Change Request Approval Alert Banner -->
        <div
          v-if="task.requestedPriority && isPmOrOwner"
          class="p-3.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-1.5 font-mono text-xs font-bold text-amber-900 dark:text-amber-200 flex-wrap">
              <span>⚡ Priority Change Requested:</span>
              <span class="px-2 py-0.5 rounded border text-[11px]" :class="getPriorityBadge(task.requestedPriority)">
                {{ task.requestedPriority }}
              </span>
            </div>
            <p v-if="task.priorityRequestReason" class="text-xs text-amber-800 dark:text-amber-300">
              <span class="font-semibold font-mono">Reason:</span> {{ task.priorityRequestReason }}
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              class="h-7 px-3 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-semibold cursor-pointer shadow-xs transition-colors"
              @click="taskStore.approvePriorityChange(task.id)"
            >
              Approve
            </button>
            <button
              type="button"
              class="h-7 px-3 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-semibold cursor-pointer shadow-xs transition-colors"
              @click="taskStore.rejectPriorityChange(task.id)"
            >
              Reject
            </button>
          </div>
        </div>

        <!-- MEMBER: Pending Priority Change Notice -->
        <div
          v-if="task.requestedPriority && isMember"
          class="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-lg text-xs"
        >
          <div class="flex items-center gap-1.5 font-mono font-semibold text-amber-900 dark:text-amber-200">
            <span>⚡ Proposed Priority:</span>
            <span class="px-1.5 py-0.5 rounded border text-[11px]" :class="getPriorityBadge(task.requestedPriority)">
              {{ task.requestedPriority }}
            </span>
            <span class="text-slate-500 dark:text-slate-400 text-[11px] font-normal">(Pending PM Approval)</span>
          </div>
          <p v-if="task.priorityRequestReason" class="text-amber-800 dark:text-amber-300 mt-1">
            {{ task.priorityRequestReason }}
          </p>
        </div>

        <!-- Title Field (tabindex 1) -->
        <div>
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
            Title
          </label>
          <div v-if="!isEditing">
            <h3
              class="text-base md:text-lg font-semibold text-slate-950 dark:text-slate-50 leading-snug hover:bg-slate-100 dark:hover:bg-slate-800/60 p-1 -m-1 rounded cursor-text"
              @click="enterEditMode"
              title="Click to edit (i)"
            >
              {{ task.title }}
            </h3>
          </div>
          <div v-else>
            <input
              ref="titleInput"
              tabindex="1"
              v-model="editTitle"
              type="text"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-indigo-500 rounded-md px-3 py-1.5 text-base font-semibold font-sans text-slate-950 dark:text-slate-50 focus:outline-none focus:ring-1 focus:ring-indigo-500 shadow-xs"
              placeholder="Task Title..."
              @input="onFieldChange"
            />
          </div>
        </div>

        <!-- Meta Grid (4 Interactive Pickers) -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 dark:bg-slate-950/60 rounded-lg border border-slate-200 dark:border-slate-800/80">
          <!-- Priority Selector (tabindex 3) -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Priority</span>
            <!-- MEMBER: Read-only Priority with Propose Priority button -->
            <div v-if="isMember" class="space-y-1">
              <span class="h-6 px-2 inline-flex items-center justify-center rounded-md border text-[11px] font-mono font-semibold uppercase" :class="getPriorityBadge(task.priority)">
                {{ task.priority }}
              </span>
              <button
                type="button"
                class="block w-full text-center h-6 px-1.5 rounded border border-indigo-300 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-[10px] font-mono font-medium cursor-pointer transition-colors"
                @click="openProposePriority"
              >
                Propose Priority
              </button>
            </div>
            <!-- PM / OWNER: Interactive Priority Selector -->
            <template v-else>
              <div v-if="!isEditing">
                <span class="h-6 px-2 inline-flex items-center justify-center rounded-md border text-[11px] font-mono font-semibold uppercase" :class="getPriorityBadge(task.priority)">
                  {{ task.priority }}
                </span>
              </div>
              <div v-else class="relative">
                <select
                  ref="prioritySelect"
                  tabindex="3"
                  v-model="editPriority"
                  class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-2 pr-6 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 appearance-none cursor-pointer font-semibold"
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
            </template>
          </div>

          <!-- Complexity Selector (tabindex 4) -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Complexity</span>
            <div v-if="!isEditing">
              <span class="font-mono text-xs font-bold text-slate-800 dark:text-slate-200">
                {{ task.complexity || 'M' }} ({{ task.complexity === 'S' ? '1pt' : task.complexity === 'M' ? '2pts' : task.complexity === 'L' ? '3pts' : '5pts' }})
              </span>
            </div>
            <div v-else class="relative">
              <select
                ref="complexitySelect"
                tabindex="4"
                v-model="editComplexity"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-2 pr-6 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 appearance-none cursor-pointer"
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

          <!-- Assignee Selector (tabindex 5) -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Assignee</span>
            <div v-if="!isEditing" class="flex items-center gap-1.5 text-xs font-mono text-slate-700 dark:text-slate-300 truncate">
              <span>{{ task.assignee || 'Unassigned' }}</span>
            </div>
            <div v-else class="relative">
              <select
                ref="assigneeSelect"
                tabindex="5"
                v-model="editAssignee"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-2 pr-6 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 appearance-none cursor-pointer"
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

          <!-- Due Date Picker (tabindex 6) -->
          <div>
            <span class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">Due Date</span>
            <div v-if="!isEditing" class="flex items-center gap-1.5 text-xs font-mono text-slate-700 dark:text-slate-300">
              <span>{{ task.dueDate ? new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'None' }}</span>
            </div>
            <div v-else>
              <input
                ref="dueDateInput"
                tabindex="6"
                v-model="editDueDate"
                type="date"
                class="w-full h-7 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-1.5 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
            class="w-full h-8 bg-white dark:bg-slate-900 border border-rose-300 dark:border-rose-800 rounded-md px-2.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-rose-500"
            placeholder="Describe what is blocking this task..."
            @input="onFieldChange"
          />
        </div>

        <!-- Description Field (tabindex 7) -->
        <div>
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
            Description
          </label>

          <!-- View Mode -->
          <div
            v-if="!isEditing"
            class="p-3.5 bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80 rounded-lg min-h-[90px] cursor-text hover:border-slate-300 dark:hover:border-slate-700"
            @click="enterEditMode"
            title="Click to edit (i)"
          >
            <p v-if="task.description" class="text-xs md:text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
              {{ task.description }}
            </p>
            <span v-else class="text-xs text-slate-400 dark:text-slate-600 italic">
              No description provided. Click to add details.
            </span>
          </div>

          <!-- Edit Mode -->
          <div v-else>
            <textarea
              ref="descriptionInput"
              tabindex="7"
              v-model="editDescription"
              rows="5"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 focus:border-indigo-500 rounded-md p-3 text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans shadow-xs leading-relaxed"
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

        <!-- Related Documents & Links -->
        <div class="space-y-2">
          <label class="block font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Related Documents & Links
          </label>

          <!-- List of documents -->
          <div v-if="task.documents && task.documents.length > 0" class="space-y-1.5">
            <div
              v-for="(doc, idx) in task.documents"
              :key="idx"
              class="flex items-center justify-between p-2 rounded-md bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80 gap-2"
            >
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <FileText class="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                <a
                  :href="doc"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-xs font-mono text-indigo-600 dark:text-indigo-400 hover:underline truncate"
                  :title="doc"
                >
                  {{ doc }}
                </a>
              </div>
              <button
                type="button"
                @click="removeDocument(idx)"
                class="p-1 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-slate-400 hover:text-rose-600 rounded cursor-pointer shrink-0 transition-colors"
                title="Remove link"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <div v-else class="text-xs text-slate-400 dark:text-slate-600 italic py-1">
            No documents attached yet.
          </div>

          <!-- Add new document link input -->
          <div class="flex items-center gap-2 pt-1">
            <input
              v-model="newDocUrl"
              type="url"
              placeholder="Paste document URL (e.g. https://github.com/...)..."
              class="flex-1 h-8 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md px-2.5 text-xs font-mono text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              @keydown.enter.prevent="addDocument"
            />
            <button
              type="button"
              @click="addDocument"
              :disabled="!newDocUrl.trim()"
              class="h-8 px-3 rounded-md bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-mono font-medium text-slate-800 dark:text-slate-200 flex items-center gap-1.5 cursor-pointer shrink-0"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>Add Link</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Footer Action Strip (Single Save Action in Edit Mode) -->
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
              <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px]">Esc</kbd> Save & Exit
            </span>
            <button
              type="button"
              class="h-7 px-3.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white dark:bg-indigo-600 dark:hover:bg-indigo-500 dark:text-white font-sans font-medium text-xs cursor-pointer shadow-xs"
              @click="saveAndExit"
            >
              Save
            </button>
          </template>
        </div>
      </div>
    </div>

    <!-- Member Propose Priority Modal Dialog -->
    <div
      v-if="isProposingPriority && task"
      class="fixed inset-0 z-60 bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs flex items-center justify-center p-3"
      @click.self="isProposingPriority = false"
    >
      <div class="bg-white dark:bg-slate-900 w-full max-w-md rounded-lg shadow-2xl border border-slate-300 dark:border-slate-800 p-5 space-y-4 text-slate-900 dark:text-slate-100">
        <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2.5">
          <h3 class="text-sm font-mono font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
            <span>⚡ Propose Priority Change</span>
          </h3>
          <button
            type="button"
            class="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
            @click="isProposingPriority = false"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-3 text-xs font-sans">
          <div>
            <label class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">
              Current Priority
            </label>
            <span class="h-6 px-2 inline-flex items-center justify-center rounded-md border text-[11px] font-mono font-semibold uppercase" :class="getPriorityBadge(task.priority)">
              {{ task.priority }}
            </span>
          </div>

          <div>
            <label class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">
              Proposed Priority
            </label>
            <select
              v-model="proposedPriority"
              class="w-full h-8 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md px-2.5 text-xs font-mono font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div>
            <label class="block font-mono text-[11px] uppercase text-slate-500 dark:text-slate-400 mb-1">
              Rationale / Reason
            </label>
            <textarea
              v-model="proposedReason"
              rows="3"
              placeholder="Explain why this priority change is necessary..."
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md p-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            ></textarea>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
          <button
            type="button"
            class="h-8 px-3 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono cursor-pointer"
            @click="isProposingPriority = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="h-8 px-3.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-semibold cursor-pointer shadow-xs"
            @click="submitPriorityProposal"
          >
            Submit Proposal
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
