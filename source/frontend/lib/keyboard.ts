import { useTaskStore } from '../stores/taskStore';
import { useThemeStore } from '../stores/themeStore';

export interface KeyboardState {
  onOpenQuickCreate: () => void;
  onOpenAIDecomposer: () => void;
  onOpenGitDiff: () => void;
  onOpenDAG: () => void;
  onOpenShortcutsHelp: () => void;
  onFocusSearch: () => void;
}

export function isInputActive(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  return (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT' ||
    // `=== true` because `isContentEditable` is not implemented everywhere
    // (jsdom leaves it undefined), and the signature promises a boolean.
    target.isContentEditable === true
  );
}

export function createKeyboardHandler(callbacks: KeyboardState) {
  function handleKeyDown(event: KeyboardEvent) {
    const taskStore = useTaskStore();
    const themeStore = useThemeStore();
    const target = event.target as HTMLElement | null;
    const isInputFocused = isInputActive(target);

    // Global escape handling
    if (event.key === 'Escape') {
      if (taskStore.activeDetailTaskId) {
        // Handled inside TaskDetailModal or fallback close
        return;
      }
      if (taskStore.editingTaskId) {
        event.preventDefault();
        taskStore.stopEditing();
        return;
      }
      if (isInputFocused && target) {
        target.blur();
        return;
      }
    }

    // Do not trigger global shortcuts if user is typing in an input
    if (isInputFocused) {
      return;
    }

    // If TaskDetailModal is open, let it handle its own internal keys ('i', 'Escape')
    if (taskStore.activeDetailTaskId) {
      return;
    }

    // Handle shift-modified keys first
    if (event.key === 'H' || (event.shiftKey && (event.key === 'h' || event.key === 'H'))) {
      if (taskStore.viewMode === 'KANBAN') {
        event.preventDefault();
        taskStore.shiftActiveKanbanTask('left');
        return;
      }
    }

    if (event.key === 'L' || (event.shiftKey && (event.key === 'l' || event.key === 'L'))) {
      if (taskStore.viewMode === 'KANBAN') {
        event.preventDefault();
        taskStore.shiftActiveKanbanTask('right');
        return;
      }
    }

    // Handle standard shortcuts
    switch (event.key) {
      case 'b': // View toggle (Table / Kanban)
        event.preventDefault();
        taskStore.toggleViewMode();
        break;

      case 't': // Toggle Light / Dark theme
        event.preventDefault();
        themeStore.toggleTheme();
        break;

      // Spatial navigation: Mode-aware
      case 'h':
      case 'ArrowLeft':
        if (taskStore.viewMode === 'KANBAN') {
          event.preventDefault();
          taskStore.moveKanbanCursor('left');
        }
        break;

      case 'l':
      case 'ArrowRight':
        if (taskStore.viewMode === 'KANBAN') {
          event.preventDefault();
          taskStore.moveKanbanCursor('right');
        }
        break;

      case 'j':
      case 'ArrowDown':
        event.preventDefault();
        if (taskStore.viewMode === 'KANBAN') {
          taskStore.moveKanbanCursor('down');
        } else {
          taskStore.selectNext();
        }
        break;

      case 'k':
      case 'ArrowUp':
        event.preventDefault();
        if (taskStore.viewMode === 'KANBAN') {
          taskStore.moveKanbanCursor('up');
        } else {
          taskStore.selectPrev();
        }
        break;

      case ' ': // Space: cycle status
        event.preventDefault();
        taskStore.cycleSelectedStatus();
        break;

      case 'Enter': // Enter: Open Task Detail Inspector
        event.preventDefault();
        if (taskStore.selectedTask) {
          taskStore.openDetail(taskStore.selectedTask.id);
        }
        break;

      case 'i': // i: Start inline title edit on Table/Kanban
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

      case 'n': // 'n': Create task (overhauls 'c')
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
