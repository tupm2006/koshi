<script lang="ts">
  import { taskStore } from '../stores/taskStore.svelte';
  import type { TaskPriority, TaskStatus } from '../types/task';
  import { Plus, X, Flag, Tag, Clock } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let title = $state('');
  let priority = $state<TaskPriority>('MEDIUM');
  let status = $state<TaskStatus>('TODO');
  let complexity = $state<'S' | 'M' | 'L' | 'XL'>('M');
  let dueDate = $state('');
  let dependencies = $state('');

  function handleCreate() {
    if (!title.trim()) return;
    const task = taskStore.createTask(title, priority, status);
    if (task) {
      if (complexity) task.complexity = complexity;
      if (dueDate) task.dueDate = new Date(dueDate).toISOString();
      if (dependencies.trim()) {
        task.dependencies = dependencies.split(/[,;\s]+/).filter(Boolean);
      }
    }
    onClose();
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<div class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel glass-panel-glow w-full max-w-lg rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[90vh] overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
          <Plus class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-base font-bold text-zinc-100">Create Task</h2>
          <p class="text-xs text-zinc-400">Add high-velocity actionable unit</p>
        </div>
      </div>
      <button class="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer min-h-[40px]" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
      <div>
        <label for="task-title" class="block font-mono text-zinc-300 mb-1.5 font-semibold">Title *</label>
        <input
          id="task-title"
          type="text"
          bind:value={title}
          placeholder="e.g., Optimize IndexedDB write buffer"
          class="w-full bg-zinc-900/90 border border-zinc-700 rounded-xl px-3.5 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 min-h-[44px]"
          onkeydown={(e) => e.key === 'Enter' && handleCreate()}
          autofocus
        />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label for="priority-select" class="block font-mono text-zinc-400 mb-1">Priority</label>
          <select
            id="priority-select"
            bind:value={priority}
            class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 min-h-[44px]"
          >
            <option value="LOW">LOW</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="HIGH">HIGH</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
        </div>

        <div>
          <label for="complexity-select" class="block font-mono text-zinc-400 mb-1">Complexity</label>
          <select
            id="complexity-select"
            bind:value={complexity}
            class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 min-h-[44px]"
          >
            <option value="S">S (Small / &lt;2h)</option>
            <option value="M">M (Medium / 1d)</option>
            <option value="L">L (Large / 2-3d)</option>
            <option value="XL">XL (Epic / 1w+)</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label for="due-date" class="block font-mono text-zinc-400 mb-1">Due Date</label>
          <input
            id="due-date"
            type="date"
            bind:value={dueDate}
            class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 min-h-[44px]"
          />
        </div>
        <div>
          <label for="dependencies" class="block font-mono text-zinc-400 mb-1">Dependencies (IDs)</label>
          <input
            id="dependencies"
            type="text"
            bind:value={dependencies}
            placeholder="e.g. TSK-101, TSK-102"
            class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 min-h-[44px]"
          />
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="pt-4 border-t border-zinc-800 flex justify-end gap-2">
      <button class="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium cursor-pointer min-h-[44px]" onclick={onClose}>
        Cancel
      </button>
      <button
        class="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer transition min-h-[44px] shadow-lg shadow-indigo-600/20"
        onclick={handleCreate}
      >
        Create Task
      </button>
    </div>
  </div>
</div>
