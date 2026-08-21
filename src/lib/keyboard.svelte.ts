import { taskStore } from '../stores/taskStore.svelte';
import type { TaskPriority } from '../types/task';

export interface KeyboardState {
  onOpenQuickCreate: () => void;
  onOpenAIDecomposer: () => void;
  onOpenGitDiff: () => void;
  onOpenDAG: () => void;
  onOpenShortcutsHelp: () => void;
  onFocusSearch: () => void;
}

export function createKeyboardHandler(callbacks: KeyboardState) {
  function handleKeyDown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    const isInputFocused =
      target &&
      (target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable);

    // Global escape handling
    if (event.key === 'Escape') {
      if (taskStore.editingTaskId) {
        event.preventDefault();
        taskStore.stopEditing();
        return;
      }
      if (isInputFocused) {
        target.blur();
        return;
      }
    }

    // Do not trigger global vim shortcuts if user is typing in an input
    if (isInputFocused) {
      return;
    }

    // Handle shortcuts
    switch (event.key) {
      case 'j':
      case 'ArrowDown':
        event.preventDefault();
        taskStore.selectNext();
        break;

      case 'k':
      case 'ArrowUp':
        event.preventDefault();
        taskStore.selectPrev();
        break;

      case ' ': // Space: cycle status
        event.preventDefault();
        taskStore.cycleSelectedStatus();
        break;

      case 'Enter': // Enter: inline edit
        event.preventDefault();
        if (taskStore.selectedTask) {
          taskStore.startEditing(taskStore.selectedTask.id);
        }
        break;

      case 'd': // Delete
      case 'Backspace':
        if (!event.metaKey && !event.ctrlKey) {
          event.preventDefault();
          taskStore.deleteSelected();
        }
        break;

      case '/': // Search
        event.preventDefault();
        callbacks.onFocusSearch();
        break;

      case 'c': // Create task
        event.preventDefault();
        callbacks.onOpenQuickCreate();
        break;

      case '1':
        event.preventDefault();
        if (taskStore.selectedTask) taskStore.setPriority(taskStore.selectedTask.id, 'LOW');
        break;
      case '2':
        event.preventDefault();
        if (taskStore.selectedTask) taskStore.setPriority(taskStore.selectedTask.id, 'MEDIUM');
        break;
      case '3':
        event.preventDefault();
        if (taskStore.selectedTask) taskStore.setPriority(taskStore.selectedTask.id, 'HIGH');
        break;
      case '4':
        event.preventDefault();
        if (taskStore.selectedTask) taskStore.setPriority(taskStore.selectedTask.id, 'CRITICAL');
        break;

      case 'a': // AI Decomposer
        event.preventDefault();
        callbacks.onOpenAIDecomposer();
        break;

      case 'g': // Git Diff Parser
        event.preventDefault();
        callbacks.onOpenGitDiff();
        break;

      case 'v': // DAG Visualizer
        event.preventDefault();
        callbacks.onOpenDAG();
        break;

      case '?': // Help
        event.preventDefault();
        callbacks.onOpenShortcutsHelp();
        break;
    }
  }

  return {
    mount: () => {
      window.addEventListener('keydown', handleKeyDown);
    },
    unmount: () => {
      window.removeEventListener('keydown', handleKeyDown);
    },
  };
}
