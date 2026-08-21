<script lang="ts">
  import type { Task, TaskPriority, TaskStatus } from '../types/task';
  import { taskStore } from '../stores/taskStore.svelte';
  import TaskContextMenu from './TaskContextMenu.svelte';
  import {
    Flame,
    Plus,
    Check,
    Edit3,
    Trash2
  } from 'lucide-svelte';

  interface Props {
    onOpenCreate: () => void;
  }

  let { onOpenCreate }: Props = $props();

  // Context menu state
  let contextMenu = $state<{ task: Task; x: number; y: number } | null>(null);

  // Inline edit title buffer
  let editInputVal = $state('');

  // Swipe state tracking for touch gestures
  let pointerState = $state<{
    taskId: string | null;
    startX: number;
    startY: number;
    currentX: number;
    isSwiping: boolean;
  }>({
    taskId: null,
    startX: 0,
    startY: 0,
    currentX: 0,
    isSwiping: false,
  });

  function getStatusDot(status: TaskStatus) {
    switch (status) {
      case 'DONE':
        return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]';
      case 'IN_PROGRESS':
        return 'bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.4)]';
      case 'BLOCKED':
        return 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.4)]';
      case 'TODO':
      default:
        return 'bg-zinc-500';
    }
  }

  function getStatusTextColor(status: TaskStatus) {
    switch (status) {
      case 'DONE':
        return 'text-emerald-400/90';
      case 'IN_PROGRESS':
        return 'text-sky-300';
      case 'BLOCKED':
        return 'text-rose-300';
      case 'TODO':
      default:
        return 'text-zinc-400';
    }
  }

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

  // Pointer & Swipe handlers
  function handlePointerDown(e: PointerEvent, task: Task) {
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    pointerState = {
      taskId: task.id,
      startX: e.clientX,
      startY: e.clientY,
      currentX: e.clientX,
      isSwiping: false,
    };
  }

  function handlePointerMove(e: PointerEvent, task: Task) {
    if (pointerState.taskId !== task.id) return;
    const deltaX = e.clientX - pointerState.startX;
    const deltaY = Math.abs(e.clientY - pointerState.startY);

    if (Math.abs(deltaX) > 12 && deltaY < 24) {
      pointerState.isSwiping = true;
      pointerState.currentX = e.clientX;
    }
  }

  function handlePointerUp(e: PointerEvent, task: Task, idx: number) {
    if (pointerState.taskId === task.id) {
      const deltaX = pointerState.currentX - pointerState.startX;
      if (pointerState.isSwiping) {
        if (deltaX > 75) {
          taskStore.setStatus(task.id, 'DONE');
        } else if (deltaX < -75) {
          if (task.status === 'BLOCKED') {
            taskStore.deleteTask(task.id);
          } else {
            taskStore.setStatus(task.id, 'BLOCKED');
          }
        }
      } else {
        taskStore.selectTask(idx);
      }
    }
    pointerState = { taskId: null, startX: 0, startY: 0, currentX: 0, isSwiping: false };
  }

  function handlePointerCancel() {
    pointerState = { taskId: null, startX: 0, startY: 0, currentX: 0, isSwiping: false };
  }

  function handleContextMenu(e: MouseEvent, task: Task, idx: number) {
    e.preventDefault();
    taskStore.selectTask(idx);
    contextMenu = { task, x: e.clientX, y: e.clientY };
  }

  function startInlineEdit(task: Task) {
    editInputVal = task.title;
    taskStore.startEditing(task.id);
  }

  function commitInlineEdit(task: Task) {
    if (editInputVal.trim() && editInputVal !== task.title) {
      taskStore.updateTask(task.id, { title: editInputVal.trim() });
    }
    taskStore.stopEditing();
  }

  function handleEditInputKeydown(e: KeyboardEvent, task: Task) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commitInlineEdit(task);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      taskStore.stopEditing();
    }
  }

  function focusElement(node: HTMLElement) {
    node.focus();
    if (node instanceof HTMLInputElement) {
      node.select();
    }
  }
</script>

<div class="relative w-full overflow-hidden flex flex-col">
  <!-- Desktop Table Header Bar -->
  <div class="hidden md:grid grid-cols-[70px_110px_1fr_80px_90px_90px_60px] items-center gap-3 px-3 py-2 text-[11px] font-mono font-medium text-zinc-500 border-b border-zinc-800/80 bg-zinc-950/40 select-none">
    <span>ID</span>
    <span>Status</span>
    <span>Title</span>
    <span>Priority</span>
    <span>Complexity</span>
    <span>Due</span>
    <span class="text-right">Actions</span>
  </div>

  <!-- Task List -->
  {#if taskStore.filteredTasks.length === 0}
    <div class="flex flex-col items-center justify-center py-20 px-4 text-center">
      <h3 class="text-sm font-semibold text-zinc-300">No tasks found</h3>
      <p class="text-xs text-zinc-500 mt-1 max-w-sm">
        Press <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono text-[10px]">c</kbd> or tap Create Task.
      </p>
      <button
        class="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono cursor-pointer transition min-h-[36px]"
        onclick={onOpenCreate}
      >
        <Plus class="w-3.5 h-3.5" />
        <span>Create Task</span>
      </button>
    </div>
  {:else}
    <div class="divide-y divide-zinc-800/40 flex flex-col" role="list">
      {#each taskStore.filteredTasks as task, idx (task.id)}
        {@const isSelected = idx === taskStore.selectedIndex}
        {@const isEditing = taskStore.editingTaskId === task.id}
        {@const isCritical = taskStore.criticalPathIds.has(task.id)}
        {@const swipeDelta = pointerState.taskId === task.id && pointerState.isSwiping ? pointerState.currentX - pointerState.startX : 0}

        <!-- Single Row Container (Desktop 38px, Mobile 44px) -->
        <div
          class="group relative touch-card select-none h-[44px] md:h-[38px] flex items-center transition-colors duration-75 {isSelected ? 'bg-zinc-900/90 border-l-2 border-zinc-400' : 'hover:bg-zinc-900/30'}"
          style="touch-action: pan-y;"
          onpointerdown={(e) => handlePointerDown(e, task)}
          onpointermove={(e) => handlePointerMove(e, task)}
          onpointerup={(e) => handlePointerUp(e, task, idx)}
          onpointercancel={handlePointerCancel}
          oncontextmenu={(e) => handleContextMenu(e, task, idx)}
          role="listitem"
        >
          <!-- Swipe Background Reveal -->
          {#if swipeDelta > 15}
            <div class="absolute inset-0 bg-emerald-950/40 border-l-2 border-emerald-500 flex items-center px-4 z-0">
              <span class="text-xs font-mono text-emerald-400 font-medium flex items-center gap-1.5">
                <Check class="w-3.5 h-3.5" /> DONE
              </span>
            </div>
          {:else if swipeDelta < -15}
            <div class="absolute inset-0 bg-rose-950/40 border-r-2 border-rose-500 flex items-center justify-end px-4 z-0">
              <span class="text-xs font-mono text-rose-400 font-medium">BLOCK / DEL</span>
            </div>
          {/if}

          <!-- Desktop Row View (>= md) -->
          <div
            class="relative z-10 hidden md:grid grid-cols-[70px_110px_1fr_80px_90px_90px_60px] items-center gap-3 px-3 w-full h-full transition-transform duration-75 {task.status === 'DONE' ? 'opacity-40' : ''}"
            style={swipeDelta !== 0 ? `transform: translateX(${swipeDelta}px);` : ''}
          >
            <!-- Col 1: ID & Critical Dot -->
            <div class="flex items-center gap-1.5 font-mono text-xs">
              <span class="text-zinc-500">{task.id}</span>
              {#if isCritical && task.status !== 'DONE'}
                <span title="Critical Path" class="text-rose-400/90">
                  <Flame class="w-3 h-3" />
                </span>
              {/if}
            </div>

            <!-- Col 2: Status -->
            <div class="flex items-center">
              <button
                class="inline-flex items-center gap-2 px-1.5 py-1 rounded hover:bg-zinc-800/60 text-xs font-mono cursor-pointer transition {getStatusTextColor(task.status)}"
                onclick={(e) => {
                  e.stopPropagation();
                  taskStore.cycleStatus(task.id);
                }}
                title="Click or Space to cycle"
              >
                <span class="w-1.5 h-1.5 rounded-full shrink-0 {getStatusDot(task.status)}"></span>
                <span class="truncate">{task.status}</span>
              </button>
            </div>

            <!-- Col 3: Title -->
            <div class="flex items-center min-w-0 pr-2 overflow-hidden">
              {#if isEditing}
                <div class="flex items-center w-full" onclick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    bind:value={editInputVal}
                    use:focusElement
                    onkeydown={(e) => handleEditInputKeydown(e, task)}
                    onblur={() => commitInlineEdit(task)}
                    class="w-full bg-zinc-950 border border-zinc-600 rounded px-2 py-0.5 text-xs text-zinc-100 focus:outline-none font-sans"
                  />
                </div>
              {:else}
                <button
                  type="button"
                  class="text-left w-full truncate text-xs font-normal text-zinc-200 hover:text-white cursor-text bg-transparent border-0 p-0 font-inherit block leading-none"
                  ondblclick={(e) => {
                    e.stopPropagation();
                    startInlineEdit(task);
                  }}
                  title="Double click or Enter to edit"
                >
                  <span class="truncate block {task.status === 'DONE' ? 'line-through text-zinc-500' : ''}">
                    {task.title}
                  </span>
                </button>
              {/if}
            </div>

            <!-- Col 4: Priority -->
            <div class="flex items-center font-mono text-[11px]">
              <button
                class="px-1.5 py-0.5 rounded border text-[10px] font-mono cursor-pointer transition {getPriorityBadge(task.priority)}"
                onclick={(e) => {
                  e.stopPropagation();
                  const priorities: TaskPriority[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
                  const next = priorities[(priorities.indexOf(task.priority) + 1) % priorities.length];
                  taskStore.setPriority(task.id, next);
                }}
                title="Click or 1-4 to change"
              >
                {task.priority}
              </button>
            </div>

            <!-- Col 5: Complexity / Dep -->
            <div class="flex items-center gap-1.5 text-[11px] text-zinc-500 font-mono truncate">
              {#if task.complexity}
                <span class="text-zinc-400">[{task.complexity}]</span>
              {/if}
              {#if task.dependencies && task.dependencies.length > 0}
                <span class="text-zinc-500 truncate" title="Deps: {task.dependencies.join(', ')}">
                  ← {task.dependencies.join(', ')}
                </span>
              {/if}
            </div>

            <!-- Col 6: Due Date -->
            <div class="flex items-center text-[11px] text-zinc-500 font-mono truncate">
              {#if task.dueDate}
                <span>{new Date(task.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
              {:else}
                <span>-</span>
              {/if}
            </div>

            <!-- Col 7: Actions -->
            <div class="flex items-center justify-end">
              <div class="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5">
                <button
                  class="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-300 cursor-pointer"
                  onclick={(e) => {
                    e.stopPropagation();
                    startInlineEdit(task);
                  }}
                  title="Rename (Enter)"
                >
                  <Edit3 class="w-3 h-3" />
                </button>
                <button
                  class="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-red-400 cursor-pointer"
                  onclick={(e) => {
                    e.stopPropagation();
                    taskStore.deleteTask(task.id);
                  }}
                  title="Delete (d)"
                >
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>

          <!-- Mobile Row View (< md) -->
          <div
            class="relative z-10 flex md:hidden items-center justify-between gap-2.5 px-3 w-full h-full transition-transform duration-75 {task.status === 'DONE' ? 'opacity-40' : ''}"
            style={swipeDelta !== 0 ? `transform: translateX(${swipeDelta}px);` : ''}
          >
            <!-- Left: Status Badge & Trigger -->
            <button
              type="button"
              class="inline-flex items-center gap-1.5 px-1.5 py-1 rounded bg-zinc-900/60 border border-zinc-800 text-[10px] font-mono cursor-pointer shrink-0 {getStatusTextColor(task.status)}"
              onclick={(e) => {
                e.stopPropagation();
                taskStore.cycleStatus(task.id);
              }}
            >
              <span class="w-1.5 h-1.5 rounded-full shrink-0 {getStatusDot(task.status)}"></span>
              <span class="font-medium">{task.status === 'IN_PROGRESS' ? 'IN PROG' : task.status}</span>
            </button>

            <!-- Center: Task Title (Single-line truncated) -->
            <div class="flex-1 min-w-0 pr-1">
              {#if isEditing}
                <div class="flex items-center w-full" onclick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    bind:value={editInputVal}
                    use:focusElement
                    onkeydown={(e) => handleEditInputKeydown(e, task)}
                    onblur={() => commitInlineEdit(task)}
                    class="w-full bg-zinc-950 border border-zinc-600 rounded px-2 py-0.5 text-xs text-zinc-100 focus:outline-none font-sans"
                  />
                </div>
              {:else}
                <button
                  type="button"
                  class="text-left w-full truncate text-xs font-normal text-zinc-200 hover:text-white cursor-text bg-transparent border-0 p-0 font-inherit block leading-none"
                  onclick={() => taskStore.selectTask(idx)}
                  ondblclick={(e) => {
                    e.stopPropagation();
                    startInlineEdit(task);
                  }}
                >
                  <span class="truncate block {task.status === 'DONE' ? 'line-through text-zinc-500' : ''}">
                    {task.title}
                  </span>
                </button>
              {/if}
            </div>

            <!-- Right: Priority & Critical Indicator -->
            <div class="flex items-center gap-1.5 shrink-0">
              {#if isCritical && task.status !== 'DONE'}
                <span title="Critical Path" class="text-rose-400">
                  <Flame class="w-3.5 h-3.5" />
                </span>
              {/if}
              <button
                type="button"
                class="px-1.5 py-0.5 rounded border text-[9px] font-mono cursor-pointer {getPriorityBadge(task.priority)}"
                onclick={(e) => {
                  e.stopPropagation();
                  const priorities: TaskPriority[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
                  const next = priorities[(priorities.indexOf(task.priority) + 1) % priorities.length];
                  taskStore.setPriority(task.id, next);
                }}
              >
                {task.priority.slice(0, 4)}
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if contextMenu}
  <TaskContextMenu
    task={contextMenu.task}
    x={contextMenu.x}
    y={contextMenu.y}
    onClose={() => (contextMenu = null)}
  />
{/if}
