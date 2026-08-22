<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useTaskStore } from './stores/taskStore';
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
  Server
} from 'lucide-vue-next';
import type { FilterStatus } from './types/task';

const taskStore = useTaskStore();

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

onMounted(() => {
  taskStore.init();
  keyboard.mount();
});

onUnmounted(() => {
  keyboard.unmount();
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
  <main class="min-h-screen min-h-[100dvh] flex flex-col bg-[#090a0f] text-zinc-200 safe-top pb-24 md:pb-6 font-sans">
    <!-- Minimal Top Navigation Bar -->
    <header class="border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-30 px-3 md:px-4 py-2">
      <div class="w-full flex items-center justify-between gap-2">
        <!-- Brand & Auth Pill -->
        <div class="flex items-center gap-2">
          <h1 class="text-xs font-bold tracking-wider text-zinc-100 font-mono">KOSHI</h1>

          <!-- View Toggle (Table / Kanban) -->
          <button
            type="button"
            class="flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] font-mono text-zinc-300 cursor-pointer"
            @click="taskStore.toggleViewMode()"
            title="Toggle Table / Kanban View"
          >
            <LayoutGrid v-if="taskStore.viewMode === 'TABLE'" class="w-3 h-3 text-indigo-400" />
            <List v-else class="w-3 h-3 text-sky-400" />
            <span>{{ taskStore.viewMode === 'TABLE' ? 'Kanban' : 'Table' }}</span>
          </button>

          <!-- Auth Status Pill -->
          <button
            type="button"
            class="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono cursor-pointer transition"
            :class="taskStore.currentUser ? 'bg-indigo-950/40 border-indigo-800 text-indigo-300' : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:text-zinc-300'"
            @click="isAuthModalOpen = true"
          >
            <Shield class="w-3 h-3" />
            <span>{{ taskStore.currentUser ? `${taskStore.currentUser.role}: ${taskStore.currentUser.full_name}` : 'Guest / Sign In' }}</span>
          </button>
        </div>

        <!-- Header Action Controls -->
        <div class="flex items-center gap-1 md:gap-1.5">
          <!-- Mandated AI Feature A: Weekly Summary -->
          <button
            type="button"
            class="hidden lg:inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-indigo-300 text-xs font-mono cursor-pointer transition"
            @click="isWeeklySummaryOpen = true"
            title="Weekly Summary (Feature A)"
          >
            <Sparkles class="w-3 h-3 text-indigo-400" />
            <span>Summary</span>
          </button>

          <!-- Mandated AI Feature B: Meeting Minutes -->
          <button
            type="button"
            class="hidden lg:inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-sky-300 text-xs font-mono cursor-pointer transition"
            @click="isMeetingMinutesOpen = true"
            title="Meeting Minutes (Feature B)"
          >
            <FileText class="w-3 h-3 text-sky-400" />
            <span>Minutes</span>
          </button>

          <!-- Mandated AI Feature C: Workload & Assignment -->
          <button
            type="button"
            class="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-amber-300 text-xs font-mono cursor-pointer transition"
            @click="isWorkloadAssignOpen = true"
            title="Team Workload & Smart Assignment (Feature C)"
          >
            <Users class="w-3 h-3 text-amber-400" />
            <span>Workload</span>
          </button>

          <!-- Goal Decomposer AI -->
          <button
            type="button"
            class="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono cursor-pointer transition"
            @click="isAIDecomposerOpen = true"
            title="AI Decomposer (a)"
          >
            <Sparkles class="w-3 h-3 text-zinc-400" />
            <span>Decompose</span>
          </button>

          <button
            type="button"
            class="hidden md:inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-mono cursor-pointer transition"
            @click="isDAGOpen = true"
            title="DAG Critical Path (v)"
          >
            <GitFork class="w-3 h-3" />
            <span>DAG</span>
          </button>

          <button
            type="button"
            class="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-mono cursor-pointer transition"
            @click="isExportImportOpen = true"
            title="JSON Backup"
          >
            <Download class="w-3 h-3" />
          </button>

          <button
            type="button"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-mono font-medium cursor-pointer transition"
            @click="isCreateModalOpen = true"
            title="Create Task (c)"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>New <kbd class="hidden sm:inline text-zinc-600 text-[10px]">c</kbd></span>
          </button>
        </div>
      </div>
    </header>

    <!-- Filter & Search Toolbar (Edge to Edge) -->
    <section class="w-full border-b border-zinc-800/60 bg-zinc-950/30 px-3 md:px-4 py-1.5 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
      <!-- Search Input -->
      <div class="relative flex-1 max-w-md">
        <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
        <input
          ref="searchInputEl"
          v-model="taskStore.filter.searchQuery"
          type="text"
          placeholder="Filter tasks... (Press /)"
          class="w-full bg-zinc-900/60 border border-zinc-800/80 rounded pl-8 pr-6 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600 font-sans"
        />
        <button
          v-if="taskStore.filter.searchQuery"
          type="button"
          class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 cursor-pointer p-0.5"
          @click="taskStore.setSearchQuery('')"
        >
          <X class="w-3 h-3" />
        </button>
      </div>

      <!-- Status Tabs -->
      <div class="flex items-center gap-1 text-xs font-mono overflow-x-auto no-scrollbar py-0.5">
        <button
          v-for="st in statusTabs"
          :key="st"
          type="button"
          class="px-2 py-0.5 rounded transition cursor-pointer shrink-0"
          :class="taskStore.filter.status === st && !taskStore.filter.onlyCriticalPath ? 'bg-zinc-800 text-zinc-100 font-medium' : 'text-zinc-500 hover:text-zinc-300'"
          @click="() => {
            if (taskStore.filter.onlyCriticalPath) taskStore.toggleCriticalPathOnly();
            taskStore.setFilterStatus(st);
          }"
        >
          {{ st }}
        </button>

        <button
          type="button"
          class="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded transition cursor-pointer shrink-0"
          :class="taskStore.filter.onlyCriticalPath ? 'bg-rose-950/40 text-rose-300 border border-rose-800/50' : 'text-zinc-500 hover:text-zinc-300'"
          @click="taskStore.toggleCriticalPathOnly()"
          title="Toggle Critical Path Only"
        >
          <Flame class="w-3 h-3 text-rose-400" />
          <span>Crit ({{ taskStore.criticalPathIds.size }})</span>
        </button>
      </div>
    </section>

    <!-- Main View (Table vs Kanban Board) -->
    <section class="w-full flex-1 flex flex-col overflow-x-auto">
      <TaskTable v-if="taskStore.viewMode === 'TABLE'" :on-open-create="() => (isCreateModalOpen = true)" />
      <KanbanBoard v-else :on-open-create="() => (isCreateModalOpen = true)" />
    </section>

    <!-- Footer with Telemetry -->
    <footer class="w-full px-3 md:px-4 py-2 border-t border-zinc-800/60 bg-zinc-950/40 flex items-center justify-between text-xs select-none">
      <div class="hidden md:flex items-center gap-2.5 font-mono text-[11px] text-zinc-500">
        <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">j</kbd>/<kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">k</kbd> Nav</span>
        <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">Space</kbd> Status</span>
        <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">Enter</kbd> Edit</span>
        <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">d</kbd> Del</span>
        <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">1-4</kbd> Priority</span>
      </div>

      <div class="flex items-center gap-2 text-slate-500 font-mono text-[11px] ml-auto">
        <span class="flex items-center gap-1">
          <Server class="w-3 h-3" :class="taskStore.isBackendConnected ? 'text-emerald-400' : 'text-zinc-600'" />
          <span>{{ taskStore.isBackendConnected ? 'FastAPI Connected' : 'Local IndexedDB' }}</span>
        </span>
        <span>•</span>
        <span>Latency: {{ taskStore.lastLatencyMs || '<0.5' }}ms</span>
        <span>•</span>
        <button
          type="button"
          class="hover:text-slate-300 underline cursor-pointer"
          @click="taskStore.resetToDefault()"
        >
          Reset sample
        </button>
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
    <AIDecomposerModal v-if="isAIDecomposerOpen" @close="isAIDecomposerOpen = false" />
    <GitDiffModal v-if="isGitDiffOpen" @close="isGitDiffOpen = false" />
    <DAGVisualizerModal v-if="isDAGOpen" @close="isDAGOpen = false" />
    <ShortcutsHelpModal v-if="isShortcutsHelpOpen" @close="isShortcutsHelpOpen = false" />
    <CreateTaskModal v-if="isCreateModalOpen" @close="isCreateModalOpen = false" />

    <!-- JSON Backup / Restore Modal -->
    <div v-if="isExportImportOpen" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 animate-in fade-in duration-100">
      <div class="glass-panel w-full max-w-md rounded-xl p-4 shadow-2xl border border-zinc-800 text-zinc-200 flex flex-col">
        <div class="flex items-center justify-between pb-2 border-b border-zinc-800">
          <h2 class="text-xs font-mono font-semibold">JSON Backup & Restore</h2>
          <button type="button" class="p-1 text-zinc-500 hover:text-zinc-300 cursor-pointer" @click="isExportImportOpen = false">
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
        <div class="py-3 space-y-3 text-xs">
          <div class="flex items-center justify-between p-2 rounded bg-zinc-900 border border-zinc-800">
            <span class="font-mono text-zinc-400">Export state file</span>
            <button
              type="button"
              class="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-mono text-xs cursor-pointer"
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
              class="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-600"
            ></textarea>
            <div v-if="importStatusMsg" class="text-[11px] font-mono text-zinc-400 mt-1">{{ importStatusMsg }}</div>
            <button
              type="button"
              class="w-full mt-2 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-mono text-xs cursor-pointer"
              @click="handleImportJSON"
            >
              Import JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
