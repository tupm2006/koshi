<script lang="ts">
  import { taskStore } from '../stores/taskStore.svelte';
  import type { Task, TaskStatus, TaskPriority } from '../types/task';
  import { Flame, Plus, ChevronLeft, ChevronRight, Clock, AlertCircle } from 'lucide-svelte';

  interface Props {
    onOpenCreate: () => void;
  }

  let { onOpenCreate }: Props = $props();

  const COLUMNS: { status: TaskStatus; label: string; dotClass: string; borderClass: string; badgeClass: string }[] = [
    { status: 'TODO', label: 'To Do', dotClass: 'bg-zinc-500', borderClass: 'border-zinc-800', badgeClass: 'text-zinc-400 bg-zinc-900 border-zinc-800' },
    { status: 'IN_PROGRESS', label: 'In Progress', dotClass: 'bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.4)]', borderClass: 'border-sky-950/60', badgeClass: 'text-sky-300 bg-sky-950/40 border-sky-800/60' },
    { status: 'BLOCKED', label: 'Blocked', dotClass: 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.4)]', borderClass: 'border-rose-950/60', badgeClass: 'text-rose-300 bg-rose-950/40 border-rose-800/60' },
    { status: 'DONE', label: 'Completed', dotClass: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]', borderClass: 'border-emerald-950/60', badgeClass: 'text-emerald-300 bg-emerald-950/40 border-emerald-800/60' },
  ];

  function getPriorityBadge(p: TaskPriority) {
    switch (p) {
      case 'CRITICAL':
        return 'bg-rose-950/60 text-rose-300 border-rose-800/80 font-bold';
      case 'HIGH':
        return 'bg-amber-950/50 text-amber-300 border-amber-800/60 font-semibold';
      case 'MEDIUM':
        return 'bg-blue-950/40 text-blue-300 border-blue-800/40';
      case 'LOW':
      default:
        return 'bg-zinc-900 text-zinc-400 border-zinc-800';
    }
  }

  function moveStatus(task: Task, direction: 'left' | 'right') {
    const order: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];
    const currIdx = order.indexOf(task.status);
    if (direction === 'left' && currIdx > 0) {
      taskStore.setStatus(task.id, order[currIdx - 1]);
    } else if (direction === 'right' && currIdx < order.length - 1) {
      taskStore.setStatus(task.id, order[currIdx + 1]);
    }
  }

  // HTML5 Drag and Drop handlers
  function handleDragStart(e: DragEvent, taskId: string) {
    if (e.dataTransfer) {
      e.dataTransfer.setData('text/plain', taskId);
      e.dataTransfer.effectAllowed = 'move';
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'move';
    }
  }

  function handleDrop(e: DragEvent, targetStatus: TaskStatus) {
    e.preventDefault();
    if (e.dataTransfer) {
      const taskId = e.dataTransfer.getData('text/plain');
      if (taskId) {
        taskStore.setStatus(taskId, targetStatus);
      }
    }
  }
</script>

<div class="w-full flex-1 p-3 md:p-4 overflow-x-auto">
  <div class="grid grid-cols-1 md:grid-cols-4 gap-3 md:gap-4 min-w-[300px] md:min-w-[900px] h-full items-start">
    {#each COLUMNS as col}
      {@const colTasks = taskStore.filteredTasks.filter((t) => t.status === col.status)}
      <div
        class="flex flex-col bg-zinc-950/50 border {col.borderClass} rounded-xl p-3 max-h-[calc(100vh-140px)] min-h-[300px]"
        ondragover={handleDragOver}
        ondrop={(e) => handleDrop(e, col.status)}
        role="region"
        aria-label="{col.label} column"
      >
        <!-- Column Header -->
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-zinc-800/80 select-none">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full {col.dotClass}"></span>
            <h3 class="text-xs font-mono font-bold text-zinc-200">{col.label}</h3>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono border {col.badgeClass}">
            {colTasks.length}
          </span>
        </div>

        <!-- Cards List -->
        <div class="flex-1 overflow-y-auto space-y-2 pr-1 no-scrollbar">
          {#if colTasks.length === 0}
            <div class="text-center py-8 text-[11px] text-zinc-600 font-mono">
              Empty column
            </div>
          {:else}
            {#each colTasks as task (task.id)}
              {@const isCritical = taskStore.criticalPathIds.has(task.id)}
              <div
                class="group bg-zinc-900/90 hover:bg-zinc-900 border border-zinc-800/80 hover:border-zinc-700 rounded-lg p-2.5 transition shadow-sm cursor-grab active:cursor-grabbing select-none"
                draggable="true"
                ondragstart={(e) => handleDragStart(e, task.id)}
                role="article"
              >
                <!-- Top Row: ID & Badges -->
                <div class="flex items-center justify-between gap-1 mb-1.5 text-[10px] font-mono">
                  <span class="text-zinc-500 font-medium">{task.id}</span>
                  <div class="flex items-center gap-1">
                    {#if isCritical && task.status !== 'DONE'}
                      <span title="Critical Path" class="text-rose-400">
                        <Flame class="w-3.5 h-3.5" />
                      </span>
                    {/if}
                    <span class="px-1.5 py-0.2 rounded border {getPriorityBadge(task.priority)}">
                      {task.priority.slice(0, 4)}
                    </span>
                  </div>
                </div>

                <!-- Title -->
                <h4 class="text-xs font-normal text-zinc-200 mb-1.5 leading-snug {task.status === 'DONE' ? 'line-through text-zinc-500' : ''}">
                  {task.title}
                </h4>

                <!-- Blocking Reason Warning -->
                {#if task.blocking_reason && task.status === 'BLOCKED'}
                  <div class="flex items-center gap-1 text-[10px] text-rose-400/90 font-mono mb-1.5 bg-rose-950/30 p-1 rounded border border-rose-900/40">
                    <AlertCircle class="w-3 h-3 shrink-0" />
                    <span class="truncate">{task.blocking_reason}</span>
                  </div>
                {/if}

                <!-- Footer Row: Due Date & Shift Controls -->
                <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-1.5 border-t border-zinc-850">
                  <div class="flex items-center gap-1">
                    {#if task.dueDate}
                      <Clock class="w-3 h-3 text-zinc-500" />
                      <span>{new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                    {:else}
                      <span>-</span>
                    {/if}
                  </div>

                  <!-- Quick Column Shift Controls -->
                  <div class="flex items-center gap-0.5 opacity-60 group-hover:opacity-100 transition">
                    {#if col.status !== 'TODO'}
                      <button
                        type="button"
                        class="p-0.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-200 cursor-pointer"
                        onclick={() => moveStatus(task, 'left')}
                        title="Move left"
                      >
                        <ChevronLeft class="w-3.5 h-3.5" />
                      </button>
                    {/if}
                    {#if col.status !== 'DONE'}
                      <button
                        type="button"
                        class="p-0.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-200 cursor-pointer"
                        onclick={() => moveStatus(task, 'right')}
                        title="Move right"
                      >
                        <ChevronRight class="w-3.5 h-3.5" />
                      </button>
                    {/if}
                  </div>
                </div>
              </div>
            {/each}
          {/if}
        </div>

        <!-- Add Task Quick Button at Column Bottom -->
        <button
          type="button"
          class="w-full mt-2 py-1.5 rounded-lg border border-dashed border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/40 text-zinc-500 hover:text-zinc-300 text-xs font-mono flex items-center justify-center gap-1 cursor-pointer transition"
          onclick={onOpenCreate}
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Task</span>
        </button>
      </div>
    {/each}
  </div>
</div>
