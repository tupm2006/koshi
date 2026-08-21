<script lang="ts">
  import type { Task, TaskPriority, TaskStatus } from '../types/task';
  import { taskStore } from '../stores/taskStore.svelte';
  import { CheckCircle2, CircleDot, AlertOctagon, CheckSquare, Trash2, Edit3, Flag } from 'lucide-svelte';

  interface Props {
    task: Task;
    x: number;
    y: number;
    onClose: () => void;
  }

  let { task, x, y, onClose }: Props = $props();

  function handleSetStatus(status: TaskStatus) {
    taskStore.setStatus(task.id, status);
    onClose();
  }

  function handleSetPriority(p: TaskPriority) {
    taskStore.setPriority(task.id, p);
    onClose();
  }

  function handleStartEdit() {
    taskStore.startEditing(task.id);
    onClose();
  }

  function handleDelete() {
    taskStore.deleteTask(task.id);
    onClose();
  }
</script>

<svelte:window onpointerdown={onClose} onkeydown={(e) => e.key === 'Escape' && onClose()} />

<!-- Context Menu Popup -->
<div
  class="fixed z-50 min-w-[200px] rounded-xl bg-zinc-900/95 p-1.5 shadow-2xl border border-zinc-700/60 backdrop-blur-xl text-xs text-zinc-200 animate-in fade-in zoom-in-95 duration-100"
  style="top: {Math.min(y, window.innerHeight - 300)}px; left: {Math.min(x, window.innerWidth - 220)}px;"
  role="menu"
  tabindex="-1"
  onpointerdown={(e) => e.stopPropagation()}
>
  <div class="px-2.5 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-400 border-b border-zinc-800">
    {task.id} Actions
  </div>

  <!-- Status options -->
  <div class="py-1">
    <div class="px-2 py-0.5 text-[10px] text-zinc-400 uppercase tracking-wider">Set Status</div>
    <button
      class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition text-left cursor-pointer min-h-[36px]"
      onclick={() => handleSetStatus('TODO')}
    >
      <CircleDot class="w-3.5 h-3.5 text-zinc-400" />
      <span>TODO</span>
    </button>
    <button
      class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition text-left cursor-pointer min-h-[36px]"
      onclick={() => handleSetStatus('IN_PROGRESS')}
    >
      <CheckCircle2 class="w-3.5 h-3.5 text-blue-400" />
      <span>IN PROGRESS</span>
    </button>
    <button
      class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition text-left cursor-pointer min-h-[36px]"
      onclick={() => handleSetStatus('BLOCKED')}
    >
      <AlertOctagon class="w-3.5 h-3.5 text-amber-400" />
      <span>BLOCKED</span>
    </button>
    <button
      class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition text-left cursor-pointer min-h-[36px]"
      onclick={() => handleSetStatus('DONE')}
    >
      <CheckSquare class="w-3.5 h-3.5 text-emerald-400" />
      <span>DONE</span>
    </button>
  </div>

  <!-- Priority options -->
  <div class="border-t border-zinc-800/80 py-1">
    <div class="px-2 py-0.5 text-[10px] text-zinc-400 uppercase tracking-wider">Priority</div>
    <div class="grid grid-cols-2 gap-1 px-1">
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800/50 hover:bg-zinc-800 text-[11px] text-zinc-300 min-h-[32px]"
        onclick={() => handleSetPriority('LOW')}
      >
        <Flag class="w-3 h-3 text-zinc-400" />
        <span>Low</span>
      </button>
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800/50 hover:bg-zinc-800 text-[11px] text-blue-300 min-h-[32px]"
        onclick={() => handleSetPriority('MEDIUM')}
      >
        <Flag class="w-3 h-3 text-blue-400" />
        <span>Med</span>
      </button>
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800/50 hover:bg-zinc-800 text-[11px] text-amber-300 min-h-[32px]"
        onclick={() => handleSetPriority('HIGH')}
      >
        <Flag class="w-3 h-3 text-amber-400" />
        <span>High</span>
      </button>
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800/50 hover:bg-zinc-800 text-[11px] text-red-300 min-h-[32px]"
        onclick={() => handleSetPriority('CRITICAL')}
      >
        <Flag class="w-3 h-3 text-red-400 font-bold" />
        <span>Crit</span>
      </button>
    </div>
  </div>

  <!-- Mutate / Delete -->
  <div class="border-t border-zinc-800/80 pt-1">
    <button
      class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 text-zinc-200 transition text-left cursor-pointer min-h-[36px]"
      onclick={handleStartEdit}
    >
      <Edit3 class="w-3.5 h-3.5 text-zinc-400" />
      <span>Inline Rename (Enter)</span>
    </button>
    <button
      class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-red-950/40 text-red-400 hover:text-red-300 transition text-left cursor-pointer min-h-[36px]"
      onclick={handleDelete}
    >
      <Trash2 class="w-3.5 h-3.5" />
      <span>Delete Task (d)</span>
    </button>
  </div>
</div>
