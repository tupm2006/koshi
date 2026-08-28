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
import GitDiffModal from './components/GitDiffModal.vue';
import DAGVisualizerModal from './components/DAGVisualizerModal.vue';
import ShortcutsHelpModal from './components/ShortcutsHelpModal.vue';
import CreateTaskModal from './components/CreateTaskModal.vue';
import TaskDetailModal from './components/TaskDetailModal.vue';
import ProjectMembersModal from './components/ProjectMembersModal.vue';
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
  ChevronDown
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
const isProjectMembersOpen = ref(false);
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
  isProjectMembersOpen.value = false;
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
  window.addEventListener('keydown', handleGlobalEscape, true);
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
    <!-- Top Navigation Header -->
    <header class="h-12 border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 shrink-0 px-3 md:px-6 flex items-center justify-between z-30 shadow-xs">
      <div class="w-full max-w-[1720px] mx-auto flex items-center justify-between gap-2">
        <!-- Left: Logo & View Mode -->
        <div class="flex items-center gap-2">
          <h1 class="text-sm font-bold tracking-wider text-slate-900 dark:text-slate-100 font-mono">
            KOSHI
          </h1>
          <button
            type="button"
            class="h-8 flex items-center gap-1.5 px-2.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200 cursor-pointer shadow-2xs"
            @click="taskStore.toggleViewMode()"
            title="Toggle Table / Kanban View (b)"
          >
            <LayoutGrid class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" v-if="taskStore.viewMode === 'TABLE'"/>
            <List class="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" v-else/>
            <span class="hidden sm:inline">{{ taskStore.viewMode === 'TABLE' ? 'Kanban' : 'Table' }}</span>
          </button>
        </div>

        <!-- Right: Actions Cluster (Desktop vs Mobile Optimized) -->
        <div class="flex items-center gap-1.5 sm:gap-2">
          <!-- User / Auth Profile -->
          <div v-if="taskStore.currentUser" class="inline-flex items-center gap-1">
            <button
              type="button"
              class="h-8 inline-flex items-center gap-1 px-2 rounded-md border text-xs font-mono cursor-pointer shadow-2xs bg-indigo-50 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 font-semibold max-w-[140px] sm:max-w-none truncate"
              @click="isAuthModalOpen = true"
              title="Account Details"
            >
              <img
                v-if="taskStore.currentUser.avatar_url"
                :src="taskStore.currentUser.avatar_url"
                alt="Avatar"
                class="w-4 h-4 rounded-full border border-indigo-400 object-cover shrink-0"
              />
              <Shield v-else class="w-3.5 h-3.5 shrink-0"/>
              <span class="truncate">{{ taskStore.currentUser.role }}: {{ taskStore.currentUser.full_name }}</span>
            </button>
            <button
              type="button"
              class="hidden sm:inline-flex h-8 px-2 items-center justify-center rounded-md border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-rose-950/40 hover:text-rose-600 dark:hover:text-rose-400 text-[11px] font-mono text-slate-500 cursor-pointer shadow-2xs"
              @click="taskStore.logout()"
              title="Sign Out"
            >
              Sign Out
            </button>
          </div>
          <button
            v-else
            type="button"
            class="h-8 inline-flex items-center gap-1 px-2.5 rounded-md border text-xs font-mono cursor-pointer shadow-2xs bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            @click="isAuthModalOpen = true"
          >
            <Shield class="w-3.5 h-3.5"/>
            <span>Sign In</span>
          </button>

          <!-- Desktop-only Actions -->
          <button
            type="button"
            class="hidden md:inline-flex h-8 items-center gap-1.5 px-2.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200 cursor-pointer"
            @click="isProjectMembersOpen = true"
            title="Team Collaborators"
          >
            <Users class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400"/>
            <span>Team</span>
          </button>

          <!-- AI Tools Menu (Desktop) -->
          <div id="ai-menu-container" class="relative hidden md:block">
            <button
              type="button"
              class="h-8 inline-flex items-center gap-1.5 px-2.5 rounded-md bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs font-mono cursor-pointer"
              @click.stop="isAIMenuOpen = !isAIMenuOpen"
            >
              <Sparkles class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400"/>
              <span>AI Tools</span>
              <ChevronDown :class="['w-3 h-3 transition-transform', isAIMenuOpen ? 'rotate-180' : '']"/>
            </button>
            <div
              v-if="isAIMenuOpen"
              class="absolute right-0 mt-1.5 w-56 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg shadow-xl py-1 z-50 text-xs font-mono"
            >
              <button class="w-full text-left px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 cursor-pointer" @click="isWeeklySummaryOpen = true; isAIMenuOpen = false">
                <Sparkles class="w-3.5 h-3.5 text-indigo-600"/> Weekly Summary
              </button>
              <button class="w-full text-left px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 cursor-pointer" @click="isMeetingMinutesOpen = true; isAIMenuOpen = false">
                <FileText class="w-3.5 h-3.5 text-sky-600"/> Meeting Minutes
              </button>
              <button class="w-full text-left px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 cursor-pointer" @click="isWorkloadAssignOpen = true; isAIMenuOpen = false">
                <Users class="w-3.5 h-3.5 text-amber-600"/> Smart Assignment
              </button>
              <div class="border-t border-slate-200 dark:border-slate-800 my-1"></div>
              <button class="w-full text-left px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-between cursor-pointer" @click="isAIDecomposerOpen = true; isAIMenuOpen = false">
                <div class="flex items-center gap-2">
                  <Sparkles class="w-3.5 h-3.5 text-slate-500"/>
                  <span>Goal Decomposer</span>
                </div>
                <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[11px] text-slate-500">a</kbd>
              </button>
            </div>
          </div>

          <!-- DAG Graph (Desktop) -->
          <button
            type="button"
            class="hidden md:inline-flex h-8 items-center gap-1.5 px-2.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono cursor-pointer"
            @click="isDAGOpen = true"
            title="DAG Critical Path (v)"
          >
            <GitFork class="w-3.5 h-3.5"/>
            <span>DAG</span>
          </button>

          <!-- Backup (Desktop) -->
          <button
            type="button"
            class="hidden md:inline-flex h-8 items-center justify-center px-2.5 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono cursor-pointer"
            @click="isExportImportOpen = true"
            title="JSON Backup & Restore"
          >
            <Download class="w-3.5 h-3.5"/>
          </button>

          <!-- Theme Toggle -->
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-300 cursor-pointer"
            @click="themeStore.toggleTheme()"
            :title="`Toggle Theme (t) - Current: ${themeStore.resolvedTheme}`"
          >
            <Sun class="w-4 h-4 text-amber-400" v-if="themeStore.isDark"/>
            <Moon class="w-4 h-4 text-slate-800" v-else/>
          </button>

          <!-- Create Task Button (Desktop) -->
          <button
            type="button"
            class="hidden sm:inline-flex h-8 items-center gap-1.5 px-3 rounded-md bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-950 font-mono font-medium text-xs cursor-pointer shadow-xs"
            @click="isCreateModalOpen = true"
          >
            <Plus class="w-3.5 h-3.5"/>
            <span>New</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Sub-Header: Search & Filter Tabs (Auto-Height on Mobile to prevent clipping) -->
    <section class="min-h-[44px] h-auto py-2 sm:h-11 sm:py-0 border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/60 px-3 md:px-6 flex items-center shrink-0 z-20 shadow-2xs">
      <div class="w-full max-w-[1720px] mx-auto flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
        <!-- Search Input -->
        <div class="relative flex-1 max-w-full sm:max-w-md">
          <Search class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"/>
          <input
            ref="searchInputEl"
            v-model="taskStore.filter.searchQuery"
            type="text"
            placeholder="Filter tasks... (Press /)"
            class="h-8 w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md pl-8 pr-7 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 font-sans"
          />
          <button
            v-if="taskStore.filter.searchQuery"
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer"
            @click="taskStore.setSearchQuery('')"
          >
            <X class="w-3.5 h-3.5"/>
          </button>
        </div>

        <!-- Filter Chips (Horizontally Scrollable on Mobile) -->
        <div class="flex items-center gap-1 text-xs font-mono overflow-x-auto no-scrollbar py-0.5 shrink-0">
          <button
            v-for="st in statusTabs"
            :key="st"
            type="button"
            :class="[
              'h-6 px-2 rounded-md cursor-pointer shrink-0 text-[11px] font-medium transition-colors',
              taskStore.filter.status === st && !taskStore.filter.onlyCriticalPath
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-bold border border-slate-300 dark:border-slate-700'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900'
            ]"
            @click="() => {
              if (taskStore.filter.onlyCriticalPath) taskStore.toggleCriticalPathOnly();
              taskStore.setFilterStatus(st);
            }"
          >
            {{ st === 'IN_PROGRESS' ? 'IN PROG' : st }}
          </button>
          <button
            type="button"
            :class="[
              'h-6 px-2 rounded-md cursor-pointer shrink-0 text-[11px] font-semibold flex items-center gap-1 border',
              taskStore.filter.onlyCriticalPath
                ? 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60'
                : 'border-transparent text-slate-600 dark:text-slate-400'
            ]"
            @click="taskStore.toggleCriticalPathOnly()"
          >
            <Flame class="w-3 h-3 text-rose-600"/>
            <span>Crit ({{ taskStore.criticalPathIds.size }})</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Main Workspace Container with Mobile Bottom Nav Clearance -->
    <main class="flex-1 min-h-0 w-full max-w-[1720px] mx-auto p-3 md:p-4 pb-24 md:pb-4 flex flex-col overflow-hidden">
      <div v-if="taskStore.viewMode === 'TABLE'" class="flex-1 min-h-0 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg shadow-xs overflow-y-auto">
        <TaskTable :on-open-create="() => (isCreateModalOpen = true)" />
      </div>
      <div v-else class="flex-1 min-h-0 overflow-x-auto overflow-y-hidden">
        <KanbanBoard :on-open-create="() => (isCreateModalOpen = true)" />
      </div>
    </main>

    <!-- Desktop Status Footer -->
    <footer class="hidden md:flex h-8 border-t border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs px-4 md:px-6 items-center justify-between shrink-0 select-none z-20">
      <div class="flex items-center gap-2 font-mono text-[11px] text-slate-500 dark:text-slate-400">
        <span><kbd class="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">b</kbd> View</span>
        <span><kbd class="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">h/j/k/l</kbd> Nav</span>
        <span><kbd class="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">Space</kbd> Status</span>
        <span><kbd class="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">n</kbd> New</span>
        <span><kbd class="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700">Enter</kbd> Detail</span>
      </div>
      <div class="flex items-center gap-2 font-mono text-xs">
        <span v-if="!taskStore.isBackendConnected" class="text-amber-600 font-semibold">Offline</span>
        <button type="button" class="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer" @click="taskStore.resetToDefault()">Reset sample</button>
      </div>
    </footer>

    <!-- Mobile Bottom Navigation -->
    <MobileBottomNav
      :on-open-create="() => (isCreateModalOpen = true)"
      :on-open-a-i-decomposer="() => (isAIDecomposerOpen = true)"
      :on-open-d-a-g="() => (isDAGOpen = true)"
      :on-open-git-diff="() => (isGitDiffOpen = true)"
      :on-focus-search="() => searchInputEl?.focus()"
    />

    <!-- Modals -->
    <WeeklySummaryModal v-if="isWeeklySummaryOpen" :on-close="() => (isWeeklySummaryOpen = false)" />
    <MeetingMinutesModal v-if="isMeetingMinutesOpen" :on-close="() => (isMeetingMinutesOpen = false)" />
    <WorkloadAssignModal v-if="isWorkloadAssignOpen" :on-close="() => (isWorkloadAssignOpen = false)" />
    <AuthModal v-if="isAuthModalOpen" @close="isAuthModalOpen = false" />
    <AIDecomposerModal v-if="isAIDecomposerOpen" @close="isAIDecomposerOpen = false" />
    <GitDiffModal v-if="isGitDiffOpen" @close="isGitDiffOpen = false" />
    <DAGVisualizerModal v-if="isDAGOpen" @close="isDAGOpen = false" />
    <ShortcutsHelpModal v-if="isShortcutsHelpOpen" @close="isShortcutsHelpOpen = false" />
    <CreateTaskModal v-if="isCreateModalOpen" @close="isCreateModalOpen = false" />
    <ProjectMembersModal v-if="isProjectMembersOpen" @close="isProjectMembersOpen = false" />
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
