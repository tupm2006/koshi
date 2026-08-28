<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useTaskStore } from './stores/taskStore';
import { useThemeStore } from './stores/themeStore';
import { createKeyboardHandler } from './lib/keyboard';
import TaskTable from './components/TaskTable.vue';
import KanbanBoard from './components/KanbanBoard.vue';
import AIDecomposerModal from './components/AIDecomposerModal.vue';
import WeeklySummaryModal from './components/WeeklySummaryModal.vue';
import MeetingMinutesModal from './components/MeetingMinutesModal.vue';
import WorkloadAssignModal from './components/WorkloadAssignModal.vue';
import AuthModal from './components/AuthModal.vue';
import ProjectDashboard from './components/ProjectDashboard.vue';
import GitDiffModal from './components/GitDiffModal.vue';
import DAGVisualizerModal from './components/DAGVisualizerModal.vue';
import ShortcutsHelpModal from './components/ShortcutsHelpModal.vue';
import CreateTaskModal from './components/CreateTaskModal.vue';
import TaskDetailModal from './components/TaskDetailModal.vue';
import MobileBottomNav from './components/MobileBottomNav.vue';
import {
  Sparkles,
  FileText,
  Users,
  Shield,
  LayoutGrid,
  List,
  GitFork,
  Download,
  Plus,
  Search,
  Flame,
  X,
  Sun,
  Moon,
  ChevronDown,
  FolderKanban,
} from 'lucide-vue-next';
import type { FilterStatus } from './types/task';

const taskStore = useTaskStore();
const themeStore = useThemeStore();

// Modal visibility states
const isAIDecomposerOpen = ref(false);
const isWeeklySummaryOpen = ref(false);
const isMeetingMinutesOpen = ref(false);
const isWorkloadAssignOpen = ref(false);
const isAuthModalOpen = ref(false);
const isGitDiffOpen = ref(false);
const isDAGOpen = ref(false);
const isShortcutsHelpOpen = ref(false);
const isCreateModalOpen = ref(false);
const isExportImportOpen = ref(false);
const isAIMenuOpen = ref(false);

const searchInputEl = ref<HTMLInputElement | null>(null);
const importJsonBuffer = ref('');
const importStatusMsg = ref<string | null>(null);

// Mount keyboard handler
const keyboard = createKeyboardHandler({
  onOpenQuickCreate: () => (isCreateModalOpen.value = true),
  onOpenAIDecomposer: () => (isAIDecomposerOpen.value = true),
  onOpenGitDiff: () => (isGitDiffOpen.value = true),
  onOpenDAG: () => (isDAGOpen.value = true),
  onOpenShortcutsHelp: () => (isShortcutsHelpOpen.value = true),
  onFocusSearch: () => {
    if (searchInputEl.value) {
      searchInputEl.value.focus();
      searchInputEl.value.select();
    }
  },
});

function closeAllModals() {
  const hadOpenModal =
    isAIDecomposerOpen.value ||
    isWeeklySummaryOpen.value ||
    isMeetingMinutesOpen.value ||
    isWorkloadAssignOpen.value ||
    isAuthModalOpen.value ||
    taskStore.isDashboardOpen ||
    isGitDiffOpen.value ||
    isDAGOpen.value ||
    isShortcutsHelpOpen.value ||
    isCreateModalOpen.value ||
    isExportImportOpen.value ||
    isAIMenuOpen.value ||
    !!taskStore.activeDetailTaskId;

  isAIDecomposerOpen.value = false;
  isWeeklySummaryOpen.value = false;
  isMeetingMinutesOpen.value = false;
  isWorkloadAssignOpen.value = false;
  isAuthModalOpen.value = false;
  taskStore.isDashboardOpen = false;
  isGitDiffOpen.value = false;
  isDAGOpen.value = false;
  isShortcutsHelpOpen.value = false;
  isCreateModalOpen.value = false;
  isExportImportOpen.value = false;
  isAIMenuOpen.value = false;
  taskStore.closeDetail();

  // Stop inline editing if active
  if (taskStore.editingTaskId) {
    taskStore.stopEditing();
  }

  // If search or any input is focused, blur it
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur();
  }

  return hadOpenModal;
}

function handleGlobalEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    // If TaskDetailModal is active, let its internal key handler deal with Edit mode exit first
    if (taskStore.activeDetailTaskId) {
      return;
    }
    closeAllModals();
  }
}

function handleWindowClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest('#ai-menu-container')) {
    isAIMenuOpen.value = false;
  }
}

onMounted(() => {
  taskStore.init();
  keyboard.mount();
  window.addEventListener('click', handleWindowClick);
  window.addEventListener('keydown', handleGlobalEscape, true); // Capture phase priority
});

onUnmounted(() => {
  keyboard.unmount();
  window.removeEventListener('click', handleWindowClick);
  window.removeEventListener('keydown', handleGlobalEscape, true);
});

function handleImportJSON() {
  if (!importJsonBuffer.value.trim()) return;
  const res = taskStore.importJSON(importJsonBuffer.value);
  if (res.success) {
    importStatusMsg.value = `Successfully imported ${res.count} tasks.`;
    setTimeout(() => {
      isExportImportOpen.value = false;
      importStatusMsg.value = null;
    }, 1200);
  } else {
    importStatusMsg.value = `Import failed: ${res.error}`;
  }
}

function handleDownloadExport() {
  const jsonStr = taskStore.exportJSON();
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `koshi-backup-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

const statusTabs: FilterStatus[] = ['ALL', 'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];
</script>

<template>
  <div class="h-screen h-[100dvh] flex flex-col bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans text-xs md:text-sm safe-top overflow-hidden">
    <!-- Top Header (Fixed h-12) -->
    <header class="h-12 border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 shrink-0 px-4 md:px-6 flex items-center justify-between z-30 shadow-xs">
      <div class="w-full max-w-[1720px] mx-auto flex items-center justify-between gap-3">
        <!-- Brand & Auth Pill -->
        <div class="flex items-center gap-2.5">
          <h1 class="text-sm font-bold tracking-wider text-slate-900 dark:text-slate-100 font-mono">KOSHI</h1>

          <!-- View Toggle (Table / Kanban) -->
          <button
            type="button"
            class="h-8 flex items-center gap-1.5 px-3 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200 cursor-pointer shadow-2xs"
            @click="taskStore.toggleViewMode()"
            title="Toggle Table / Kanban View"
          >
            <LayoutGrid v-if="taskStore.viewMode === 'TABLE'" class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <List v-else class="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
            <span>{{ taskStore.viewMode === 'TABLE' ? 'Kanban' : 'Table' }}</span>
          </button>

          <!-- Project switcher / dashboard -->
          <button
            v-if="taskStore.currentUser"
            type="button"
            class="h-8 inline-flex items-center gap-1.5 px-3 rounded-md border text-xs font-mono cursor-pointer shadow-2xs bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 max-w-[220px]"
            title="My dashboard: projects and per-project roles"
            @click="taskStore.isDashboardOpen = true"
          >
            <FolderKanban class="w-3.5 h-3.5 shrink-0" />
            <span class="truncate">{{ taskStore.currentProject?.name ?? 'No project' }}</span>
          </button>

          <!-- Auth Status Pill -->
          <button
            type="button"
            class="h-8 hidden sm:inline-flex items-center gap-1.5 px-3 rounded-md border text-xs font-mono cursor-pointer shadow-2xs"
            :class="taskStore.currentUser ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 font-semibold' : 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'"
            @click="isAuthModalOpen = true"
          >
            <Shield class="w-3.5 h-3.5" />
            <span>{{ taskStore.currentUser ? `${taskStore.myRole ?? '—'}: ${taskStore.currentUser.full_name}` : 'Guest / Sign In' }}</span>
          </button>
        </div>

        <!-- Header Action Controls -->
        <div class="flex items-center gap-1.5 md:gap-2">
          <!-- Consolidated AI Tools Dropdown -->
          <div id="ai-menu-container" class="relative">
            <button
              type="button"
              class="h-8 inline-flex items-center gap-1.5 px-3 rounded-md bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs font-mono cursor-pointer shadow-2xs font-semibold"
              @click.stop="isAIMenuOpen = !isAIMenuOpen"
              title="AI Workflows & Tools"
            >
              <Sparkles class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>AI Tools</span>
              <ChevronDown class="w-3 h-3-transform" :class="isAIMenuOpen ? 'rotate-180' : ''" />
            </button>

            <!-- Dropdown Menu -->
            <div
              v-if="isAIMenuOpen"
              class="absolute right-0 mt-1.5 w-64 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg shadow-xl py-1.5 z-50 text-xs font-mono"
            >
              <button
                type="button"
                class="w-full text-left px-3 py-2 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-slate-800 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 flex items-center gap-2 cursor-pointer"
                @click="() => { isWeeklySummaryOpen = true; isAIMenuOpen = false; }"
              >
                <Sparkles class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                <div class="flex flex-col">
                  <span class="font-semibold">Weekly Summary</span>
                  <span class="text-[11px] text-slate-500 dark:text-slate-400">Progress, blockers & priorities</span>
                </div>
              </button>

              <button
                type="button"
                class="w-full text-left px-3 py-2 hover:bg-sky-50 dark:hover:bg-sky-950/40 text-slate-800 dark:text-slate-200 hover:text-sky-600 dark:hover:text-sky-400 flex items-center gap-2 cursor-pointer"
                @click="() => { isMeetingMinutesOpen = true; isAIMenuOpen = false; }"
              >
                <FileText class="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
                <div class="flex flex-col">
                  <span class="font-semibold">Meeting Minutes</span>
                  <span class="text-[11px] text-slate-500 dark:text-slate-400">Action items & decisions</span>
                </div>
              </button>

              <button
                type="button"
                class="w-full text-left px-3 py-2 hover:bg-amber-50 dark:hover:bg-amber-950/40 text-slate-800 dark:text-slate-200 hover:text-amber-600 dark:hover:text-amber-400 flex items-center gap-2 cursor-pointer"
                @click="() => { isWorkloadAssignOpen = true; isAIMenuOpen = false; }"
              >
                <Users class="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                <div class="flex flex-col">
                  <span class="font-semibold">Smart Assignment</span>
                  <span class="text-[11px] text-slate-500 dark:text-slate-400">Capacity & skill matching</span>
                </div>
              </button>

              <div class="border-t border-slate-200 dark:border-slate-800 my-1"></div>

              <button
                type="button"
                class="w-full text-left px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 flex items-center justify-between cursor-pointer"
                @click="() => { isAIDecomposerOpen = true; isAIMenuOpen = false; }"
              >
                <div class="flex items-center gap-2">
                  <Sparkles class="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                  <span>Goal Decomposer</span>
                </div>
                <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[11px] text-slate-500">a</kbd>
              </button>
            </div>
          </div>

          <!-- DAG Graph -->
          <button
            type="button"
            class="h-8 inline-flex items-center gap-1.5 px-3 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono cursor-pointer shadow-2xs"
            @click="isDAGOpen = true"
            title="DAG Critical Path (v)"
          >
            <GitFork class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">DAG</span>
          </button>

          <!-- JSON Backup -->
          <button
            type="button"
            class="h-8 inline-flex items-center justify-center px-2.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono cursor-pointer shadow-2xs"
            @click="isExportImportOpen = true"
            title="JSON Backup & Restore"
          >
            <Download class="w-3.5 h-3.5" />
          </button>

          <!-- Theme Toggle Button -->
          <button
            type="button"
            class="h-8 inline-flex items-center justify-center px-2.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-300 text-xs font-mono cursor-pointer shadow-2xs"
            @click="themeStore.toggleTheme()"
            :title="`Toggle Theme (t) - Current: ${themeStore.resolvedTheme}`"
          >
            <Sun v-if="themeStore.isDark" class="w-4 h-4 text-amber-400" />
            <Moon v-else class="w-4 h-4 text-slate-800" />
          </button>

          <!-- Create Task -->
          <button
            type="button"
            class="h-8 inline-flex items-center gap-1.5 px-3 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-50 dark:bg-slate-100 dark:hover:bg-white dark:text-slate-950 text-xs font-mono font-medium cursor-pointer shadow-xs"
            @click="isCreateModalOpen = true"
            title="Create Task (c)"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>New <kbd class="hidden sm:inline opacity-70 text-[11px]">c</kbd></span>
          </button>
        </div>
      </div>
    </header>

    <!-- Toolbar (Fixed h-11) -->
    <section class="h-11 border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/60 px-4 md:px-6 flex items-center justify-between shrink-0 z-20 shadow-2xs">
      <div class="w-full max-w-[1720px] mx-auto flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <!-- Search Input -->
        <div class="relative flex-1 max-w-md">
          <Search class="w-4 h-4 text-slate-500 dark:text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            ref="searchInputEl"
            v-model="taskStore.filter.searchQuery"
            type="text"
            placeholder="Filter tasks... (Press /)"
            class="h-7 w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md pl-9 pr-7 text-xs md:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 dark:focus:border-slate-600 font-sans shadow-2xs"
          />
          <button
            v-if="taskStore.filter.searchQuery"
            type="button"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-800 dark:text-slate-500 dark:hover:text-slate-300 cursor-pointer p-0.5"
            @click="taskStore.setSearchQuery('')"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Status Tabs (h-6 Compact) -->
        <div class="flex items-center gap-1.5 text-xs font-mono overflow-x-auto no-scrollbar py-0.5">
          <button
            v-for="st in statusTabs"
            :key="st"
            type="button"
            class="h-6 px-2.5 inline-flex items-center justify-center rounded-md cursor-pointer shrink-0 text-[11px]"
            :class="taskStore.filter.status === st && !taskStore.filter.onlyCriticalPath ? 'bg-slate-200 text-slate-900 dark:bg-slate-800 dark:text-slate-100 font-semibold border border-slate-300 dark:border-transparent shadow-2xs' : 'text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'"
            @click="() => {
              if (taskStore.filter.onlyCriticalPath) taskStore.toggleCriticalPathOnly();
              taskStore.setFilterStatus(st);
            }"
          >
            {{ st }}
          </button>

          <button
            type="button"
            class="h-6 ml-1 inline-flex items-center gap-1 px-2.5 rounded-md cursor-pointer shrink-0 text-[11px]"
            :class="taskStore.filter.onlyCriticalPath ? 'bg-rose-100 text-rose-800 border border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/50 font-semibold shadow-2xs' : 'text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'"
            @click="taskStore.toggleCriticalPathOnly()"
            title="Toggle Critical Path Only"
          >
            <Flame class="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
            <span>Crit ({{ taskStore.criticalPathIds.size }})</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Workspace Body (Full-Viewport Docked Layout) -->
    <div class="flex-1 min-h-0 w-full max-w-[1720px] mx-auto p-4 flex flex-col overflow-hidden">
      <!-- No project selected: a signed-in account with no membership yet has
           nothing to show on the board, so point it at the dashboard rather
           than rendering an empty grid with no way forward. -->
      <div
        v-if="taskStore.currentUser && taskStore.currentProjectId === null"
        class="flex-1 min-h-0 flex items-center justify-center"
      >
        <div class="max-w-md text-center p-8 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900">
          <div class="mx-auto w-11 h-11 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <FolderKanban class="w-5 h-5" />
          </div>
          <h2 class="mt-3 text-sm font-semibold font-sans">No projects yet</h2>
          <p class="mt-1.5 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Create your first project and you will be its Project Manager — or ask a
            PM to add you to theirs. Roles are set per project.
          </p>
          <button
            type="button"
            class="mt-4 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs inline-flex items-center gap-1.5 cursor-pointer"
            @click="taskStore.isDashboardOpen = true"
          >
            <FolderKanban class="w-3.5 h-3.5" />
            <span>Open dashboard</span>
          </button>
        </div>
      </div>

      <!-- Table View: Docked full-height table card -->
      <div v-else-if="taskStore.viewMode === 'TABLE'" class="flex-1 min-h-0 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg shadow-xs overflow-y-auto">
        <TaskTable :on-open-create="() => (isCreateModalOpen = true)" />
      </div>

      <!-- Kanban View: Docked horizontal column scroll -->
      <div v-else class="flex-1 min-h-0 overflow-x-auto overflow-y-hidden">
        <KanbanBoard :on-open-create="() => (isCreateModalOpen = true)" />
      </div>
    </div>

    <!-- Footer (Fixed h-9) -->
    <footer class="h-9 border-t border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs shrink-0 px-4 md:px-6 flex items-center justify-between select-none z-20">
      <div class="w-full max-w-[1720px] mx-auto flex items-center justify-between gap-3">
        <div class="hidden md:flex items-center gap-2.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">b</kbd> View</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">h/j/k/l</kbd> Nav</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">H/L</kbd> Shift</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">Space</kbd> Status</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">n</kbd> New</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">i</kbd> Edit</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">Enter</kbd> Detail</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">d</kbd> Del</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">1-4</kbd> Priority</span>
          <span><kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200">t</kbd> Theme</span>
        </div>

        <div class="flex items-center gap-2.5 font-mono text-xs ml-auto">
          <!-- Offline Warning Badge -->
          <span
            v-if="!taskStore.isBackendConnected"
            class="h-6 inline-flex items-center gap-1.5 px-2 rounded-md bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800/60 font-semibold"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>Offline (Local buffer)</span>
          </span>

          <!-- Reset action -->
          <button
            type="button"
            class="text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer font-medium"
            @click="taskStore.resetToDefault()"
          >
            Reset sample
          </button>
        </div>
      </div>
    </footer>

    <!-- Mobile Thumb Bar -->
    <MobileBottomNav
      :on-open-create="() => (isCreateModalOpen = true)"
      :on-open-a-i-decomposer="() => (isAIDecomposerOpen = true)"
      :on-open-d-a-g="() => (isDAGOpen = true)"
      :on-open-git-diff="() => (isGitDiffOpen = true)"
      :on-focus-search="() => {
        if (searchInputEl) searchInputEl.focus();
      }"
    />

    <!-- Modals -->
    <WeeklySummaryModal v-if="isWeeklySummaryOpen" :on-close="() => (isWeeklySummaryOpen = false)" />
    <MeetingMinutesModal v-if="isMeetingMinutesOpen" :on-close="() => (isMeetingMinutesOpen = false)" />
    <WorkloadAssignModal v-if="isWorkloadAssignOpen" :on-close="() => (isWorkloadAssignOpen = false)" />
    <AuthModal v-if="isAuthModalOpen" @close="isAuthModalOpen = false" />
    <ProjectDashboard v-if="taskStore.isDashboardOpen" @close="taskStore.isDashboardOpen = false" />
    <AIDecomposerModal v-if="isAIDecomposerOpen" @close="isAIDecomposerOpen = false" />
    <GitDiffModal v-if="isGitDiffOpen" @close="isGitDiffOpen = false" />
    <DAGVisualizerModal v-if="isDAGOpen" @close="isDAGOpen = false" />
    <ShortcutsHelpModal v-if="isShortcutsHelpOpen" @close="isShortcutsHelpOpen = false" />
    <CreateTaskModal v-if="isCreateModalOpen" @close="isCreateModalOpen = false" />
    <TaskDetailModal
      v-if="taskStore.activeDetailTaskId"
      :task-id="taskStore.activeDetailTaskId"
      @close="taskStore.closeDetail()"
    />

    <!-- JSON Backup / Restore Modal -->
    <div
      v-if="isExportImportOpen"
      class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/70 backdrop-blur-xs flex items-center justify-center p-3"
      @click.self="isExportImportOpen = false"
    >
      <div class="bg-white dark:bg-slate-900 w-full max-w-md rounded-lg p-4 shadow-2xl border border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col">
        <div class="flex items-center justify-between pb-2 border-b border-slate-300 dark:border-slate-800">
          <h2 class="text-xs font-mono font-semibold">JSON Backup & Restore</h2>
          <button type="button" class="p-1 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer" @click="isExportImportOpen = false">
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
        <div class="py-3 space-y-3 text-xs">
          <div class="flex items-center justify-between p-2 rounded-md bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800">
            <span class="font-mono text-slate-600 dark:text-slate-400">Export state file</span>
            <button
              type="button"
              class="h-8 px-3 rounded-md bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-mono text-xs cursor-pointer"
              @click="handleDownloadExport"
            >
              Download
            </button>
          </div>
          <div>
            <textarea
              v-model="importJsonBuffer"
              rows="4"
              placeholder="Paste JSON..."
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-md p-2 text-xs font-mono text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 dark:focus:border-slate-600"
            ></textarea>
            <div v-if="importStatusMsg" class="text-[11px] font-mono text-slate-600 dark:text-slate-400 mt-1">{{ importStatusMsg }}</div>
            <button
              type="button"
              class="w-full mt-2 h-8 rounded-md bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-mono text-xs cursor-pointer flex items-center justify-center"
              @click="handleImportJSON"
            >
              Import JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
