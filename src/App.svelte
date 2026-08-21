<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { taskStore } from './stores/taskStore.svelte';
  import { createKeyboardHandler } from './lib/keyboard.svelte';
  import TaskTable from './components/TaskTable.svelte';
  import AIDecomposerModal from './components/AIDecomposerModal.svelte';
  import GitDiffModal from './components/GitDiffModal.svelte';
  import DAGVisualizerModal from './components/DAGVisualizerModal.svelte';
  import ShortcutsHelpModal from './components/ShortcutsHelpModal.svelte';
  import CreateTaskModal from './components/CreateTaskModal.svelte';
  import MobileBottomNav from './components/MobileBottomNav.svelte';
  import {
    Sparkles,
    GitPullRequest,
    GitFork,
    Keyboard,
    Download,
    Plus,
    Search,
    Flame,
    X
  } from 'lucide-svelte';

  // Modal visibility states
  let isAIDecomposerOpen = $state(false);
  let isGitDiffOpen = $state(false);
  let isDAGOpen = $state(false);
  let isShortcutsHelpOpen = $state(false);
  let isCreateModalOpen = $state(false);
  let isExportImportOpen = $state(false);

  let searchInputEl = $state<HTMLInputElement | null>(null);
  let importJsonBuffer = $state('');
  let importStatusMsg = $state<string | null>(null);

  // Mount keyboard handler
  const keyboard = createKeyboardHandler({
    onOpenQuickCreate: () => (isCreateModalOpen = true),
    onOpenAIDecomposer: () => (isAIDecomposerOpen = true),
    onOpenGitDiff: () => (isGitDiffOpen = true),
    onOpenDAG: () => (isDAGOpen = true),
    onOpenShortcutsHelp: () => (isShortcutsHelpOpen = true),
    onFocusSearch: () => {
      if (searchInputEl) {
        searchInputEl.focus();
        searchInputEl.select();
      }
    },
  });

  onMount(() => {
    keyboard.mount();
  });

  onDestroy(() => {
    keyboard.unmount();
  });

  function handleImportJSON() {
    if (!importJsonBuffer.trim()) return;
    const res = taskStore.importJSON(importJsonBuffer);
    if (res.success) {
      importStatusMsg = `Successfully imported ${res.count} tasks.`;
      setTimeout(() => {
        isExportImportOpen = false;
        importStatusMsg = null;
      }, 1200);
    } else {
      importStatusMsg = `Import failed: ${res.error}`;
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
</script>

<main class="min-h-screen min-h-[100dvh] flex flex-col bg-[#090a0f] text-zinc-200 safe-top pb-24 md:pb-6 font-sans">
  <!-- Minimal Top Navigation Bar -->
  <header class="border-b border-zinc-800/60 bg-zinc-950/60 backdrop-blur-md sticky top-0 z-30 px-3 md:px-4 py-2">
    <div class="w-full flex items-center justify-between gap-3">
      <!-- Minimal Brand -->
      <div class="flex items-center gap-2.5">
        <h1 class="text-xs font-bold tracking-wider text-zinc-100 font-mono">KOSHI</h1>
        <span class="text-[10px] font-mono text-zinc-500 border border-zinc-800 px-1 py-0.5 rounded">
          {taskStore.filteredTasks.length}/{taskStore.tasks.length}
        </span>
      </div>

      <!-- Header Action Controls -->
      <div class="flex items-center gap-1.5 md:gap-2">
        <button
          class="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono cursor-pointer transition"
          onclick={() => (isAIDecomposerOpen = true)}
          title="AI Decomposer (a)"
        >
          <Sparkles class="w-3 h-3 text-zinc-400" />
          <span>AI <kbd class="text-zinc-500 text-[10px]">a</kbd></span>
        </button>

        <button
          class="hidden md:inline-flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono cursor-pointer transition"
          onclick={() => (isGitDiffOpen = true)}
          title="Git Diff (g)"
        >
          <GitPullRequest class="w-3 h-3 text-zinc-400" />
          <span>Diff <kbd class="text-zinc-500 text-[10px]">g</kbd></span>
        </button>

        <button
          class="hidden md:inline-flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono cursor-pointer transition"
          onclick={() => (isDAGOpen = true)}
          title="DAG Critical Path (v)"
        >
          <GitFork class="w-3 h-3 text-zinc-400" />
          <span>DAG <kbd class="text-zinc-500 text-[10px]">v</kbd></span>
        </button>

        <button
          class="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-mono cursor-pointer transition"
          onclick={() => (isExportImportOpen = true)}
          title="JSON Backup"
        >
          <Download class="w-3 h-3" />
        </button>

        <button
          class="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-mono cursor-pointer transition"
          onclick={() => (isShortcutsHelpOpen = true)}
          title="Shortcuts (?)"
        >
          <Keyboard class="w-3 h-3" />
        </button>

        <button
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-mono font-medium cursor-pointer transition"
          onclick={() => (isCreateModalOpen = true)}
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
        bind:this={searchInputEl}
        type="text"
        bind:value={taskStore.filter.searchQuery}
        placeholder="Filter tasks... (Press /)"
        class="w-full bg-zinc-900/60 border border-zinc-800/80 rounded pl-8 pr-6 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600 font-sans"
      />
      {#if taskStore.filter.searchQuery}
        <button
          class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 cursor-pointer p-0.5"
          onclick={() => taskStore.setSearchQuery('')}
        >
          <X class="w-3 h-3" />
        </button>
      {/if}
    </div>

    <!-- Status Tabs -->
    <div class="flex items-center gap-1 text-xs font-mono overflow-x-auto no-scrollbar py-0.5">
      {#each (['ALL', 'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'] as const) as st}
        <button
          class="px-2 py-0.5 rounded transition cursor-pointer shrink-0 {taskStore.filter.status === st && !taskStore.filter.onlyCriticalPath ? 'bg-zinc-800 text-zinc-100 font-medium' : 'text-zinc-500 hover:text-zinc-300'}"
          onclick={() => {
            if (taskStore.filter.onlyCriticalPath) taskStore.toggleCriticalPathOnly();
            taskStore.setFilterStatus(st);
          }}
        >
          {st}
        </button>
      {/each}

      <button
        class="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded transition cursor-pointer shrink-0 {taskStore.filter.onlyCriticalPath ? 'bg-rose-950/40 text-rose-300 border border-rose-800/50' : 'text-zinc-500 hover:text-zinc-300'}"
        onclick={() => taskStore.toggleCriticalPathOnly()}
        title="Toggle Critical Path Only"
      >
        <Flame class="w-3 h-3 text-rose-400" />
        <span>Crit ({taskStore.criticalPathIds.size})</span>
      </button>
    </div>
  </section>

  <!-- Main Edge-to-Edge Task Table -->
  <section class="w-full flex-1 overflow-x-auto">
    <TaskTable onOpenCreate={() => (isCreateModalOpen = true)} />
  </section>

  <!-- Subtle Footer with Telemetry at Bottom Right -->
  <footer class="w-full px-3 md:px-4 py-2 border-t border-zinc-800/60 bg-zinc-950/40 flex items-center justify-between text-xs select-none">
    <div class="hidden md:flex items-center gap-2.5 font-mono text-[11px] text-zinc-500">
      <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">j</kbd>/<kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">k</kbd> Nav</span>
      <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">Space</kbd> Status</span>
      <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">Enter</kbd> Edit</span>
      <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">d</kbd> Del</span>
      <span><kbd class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">1-4</kbd> Priority</span>
    </div>

    <!-- Telemetry & Reset in Low-Opacity Monospace Text -->
    <div class="flex items-center gap-3 text-slate-600 font-mono text-xs ml-auto">
      <span>RAM: &lt;15MB</span>
      <span>•</span>
      <span>Latency: {taskStore.lastLatencyMs || '&lt;0.5'}ms</span>
      <span>•</span>
      <button
        class="hover:text-slate-400 underline cursor-pointer"
        onclick={() => taskStore.resetToDefault()}
      >
        Reset sample tasks
      </button>
    </div>
  </footer>

  <!-- Mobile Thumb Bar -->
  <MobileBottomNav
    onOpenCreate={() => (isCreateModalOpen = true)}
    onOpenAIDecomposer={() => (isAIDecomposerOpen = true)}
    onOpenDAG={() => (isDAGOpen = true)}
    onOpenGitDiff={() => (isGitDiffOpen = true)}
    onFocusSearch={() => {
      if (searchInputEl) searchInputEl.focus();
    }}
  />

  <!-- Modals -->
  {#if isAIDecomposerOpen}
    <AIDecomposerModal onClose={() => (isAIDecomposerOpen = false)} />
  {/if}

  {#if isGitDiffOpen}
    <GitDiffModal onClose={() => (isGitDiffOpen = false)} />
  {/if}

  {#if isDAGOpen}
    <DAGVisualizerModal onClose={() => (isDAGOpen = false)} />
  {/if}

  {#if isShortcutsHelpOpen}
    <ShortcutsHelpModal onClose={() => (isShortcutsHelpOpen = false)} />
  {/if}

  {#if isCreateModalOpen}
    <CreateTaskModal onClose={() => (isCreateModalOpen = false)} />
  {/if}

  {#if isExportImportOpen}
    <div class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 animate-in fade-in duration-100">
      <div class="glass-panel w-full max-w-md rounded-xl p-4 shadow-2xl border border-zinc-800 text-zinc-200 flex flex-col">
        <div class="flex items-center justify-between pb-2 border-b border-zinc-800">
          <h2 class="text-xs font-mono font-semibold">JSON Backup & Restore</h2>
          <button class="p-1 text-zinc-500 hover:text-zinc-300 cursor-pointer" onclick={() => (isExportImportOpen = false)}>
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
        <div class="py-3 space-y-3 text-xs">
          <div class="flex items-center justify-between p-2 rounded bg-zinc-900 border border-zinc-800">
            <span class="font-mono text-zinc-400">Export state file</span>
            <button
              class="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-mono text-xs cursor-pointer"
              onclick={handleDownloadExport}
            >
              Download
            </button>
          </div>
          <div>
            <textarea
              bind:value={importJsonBuffer}
              rows="4"
              placeholder="Paste JSON..."
              class="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-600"
            ></textarea>
            {#if importStatusMsg}
              <div class="text-[11px] font-mono text-zinc-400 mt-1">{importStatusMsg}</div>
            {/if}
            <button
              class="w-full mt-2 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-mono text-xs cursor-pointer"
              onclick={handleImportJSON}
            >
              Import JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</main>
