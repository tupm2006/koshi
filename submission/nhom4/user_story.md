# Agile User Stories & Acceptance Criteria - Koshi Engine

## Epic 1: Task Management & Spatial Workspaces

### US-01: Keyboard-First Task Navigation
- **As a** Software Engineer,
- **I want to** navigate tasks using Vim-style hotkeys (`j`/`k` or arrows),
- **So that** I can manage my work without taking my hands off the keyboard.
- **Acceptance Criteria**:
  - **Given** I am on the Table or Kanban view,
  - **When** I press `j` or `Down`, the selection moves down to the next task within 0ms.
  - **When** I press `k` or `Up`, the selection moves up to the previous task within 0ms.
  - **Then** the active task is highlighted with a high-contrast focus ring (`ring-1 ring-indigo-500/20`).

### US-02: Circular Lateral Kanban Shifting
- **As a** Developer,
- **I want to** shift tasks between workflow stages with `Shift+H` and `Shift+L`,
- **So that** I can update task progression with automatic circular wrapping.
- **Acceptance Criteria**:
  - **Given** I have a task selected in the `DONE` column (Column 3),
  - **When** I press `Shift+L`,
  - **Then** the task's status wraps to `TODO` (Column 0) with zero page flicker.

### US-03: Interactive Task Detail Inspector
- **As a** Project Manager or Developer,
- **I want to** inspect and edit all task attributes inside a modal with `Enter`,
- **So that** I can update titles, assignees, priorities, due dates, and acceptance criteria in one place.
- **Acceptance Criteria**:
  - **Given** a task is highlighted,
  - **When** I press `Enter`, the Task Detail Inspector opens with the Title auto-focused.
  - **When** I change any field, the changes are auto-saved to local state and backend.
  - **When** I press `Escape`, the inspector saves and dismisses cleanly.

---

## Epic 2: Dependency Analysis & Critical Path Method

### US-04: DAG Cycle Prevention & Critical Path Calculation
- **As a** Technical Lead,
- **I want to** define task prerequisites and automatically detect the project's Critical Path,
- **So that** I can prevent scheduling bottlenecks and ensure zero cyclic dependency deadlocks.
- **Acceptance Criteria**:
  - **Given** a set of tasks with declared dependencies,
  - **When** the DAG is evaluated, all tasks on the zero-float path are marked with `🔥 CRITICAL PATH`.
  - **When** a user attempts to link Task A $\to$ Task B $\to$ Task A, the system rejects the operation with a cycle validation error.

---

## Epic 3: AI-Powered Project Management Assistance

### US-05: Executive Weekly Sprint Summary
- **As a** Project Manager,
- **I want to** generate a structured bulleted summary of the active sprint with one click,
- **So that** I can immediately brief stakeholders on completed deliverables and blockers.
- **Acceptance Criteria**:
  - **Given** active sprint tasks with statuses and blocking reasons,
  - **When** I trigger Weekly Summary,
  - **Then** an executive report is generated categorized by Highlights, In-Flight Tasks, and Blockers within 2 seconds.

### US-06: Meeting Minutes Action Item Extraction
- **As a** Scrum Master,
- **I want to** paste raw unstructured meeting notes and have AI extract actionable tasks,
- **So that** I do not have to manually format backlog items after standups.
- **Acceptance Criteria**:
  - **Given** unformatted raw meeting notes,
  - **When** I submit the notes to the Meeting Minutes Assistant,
  - **Then** structured tasks with titles, assignees, and complexity estimates are produced and ready to commit to the backlog.
