# ==============================================================================
# KOSHI (輿): USER REQUIREMENTS DOCUMENT (URD) & SYSTEM REQUIREMENTS SPECIFICATION (SRS)
# ==============================================================================
# System: Koshi Local-First High-Velocity Project Management System
# Production URL: https://koshi.felixsu.qzz.io
# Author: Felix Anderson (felixsu)
# Architecture: Vue 3 (Composition API / Pinia / TypeScript / Tailwind CSS) + FastAPI (Python 3.11 / SQLite / Gemini AI)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. USER REQUIREMENTS DOCUMENT (URD)
# ------------------------------------------------------------------------------

## 1.1 Purpose & Scope
- **Purpose**: Define the operational and functional requirements for Koshi, a lightweight, keyboard-first, local-first project management system designed for ultra-high velocity development workflows without cloud bloat or virtual DOM lag.
- **Scope**: Encompasses high-density table view with inline editing, 2D Kanban board with modal-less Vim navigation, cyclic state transitions, topological DAG dependency resolution, deterministic AI workflows (Weekly Progress Summary, Meeting Minutes Generator, Team Workload Balancing, Goal Decomposition), Git diff analysis, and local-first IndexedDB persistence with cloud backend synchronization.

## 1.2 User Personas & Problem Invariants
- **Lead Architect / Senior Engineer**: Requires zero-latency (< 50ms) task navigation, modal-less keyboard hotkeys, and dependency bottleneck identification without clicking through bloated multi-level forms.
- **Project Manager / Tech Lead**: Needs automated extraction of actionable tasks from messy meeting transcripts and balanced workload allocation without manual heuristic guessing.
- **Offline / Field Developer**: Needs uninterrupted execution offline with background synchronization once the network is restored.

## 1.3 User Requirements Matrix (MoSCoW)

### Must Have (Core Invariants)
- **URD-FR-01 [Dual-Mode Views]**: The system shall provide seamless toggling between a high-density Table View and a 4-column 2D Kanban Board (`b` hotkey).
- **URD-FR-02 [Vim Keyboard Ergonomics]**: The system shall support full modal-less keyboard navigation:
  - Table: `j`/`k` vertical row traversal.
  - Kanban: `h`/`j`/`k`/`l` 2D spatial grid traversal.
  - Status Mutation: `Space` circular status cycling (`TODO` $\to$ `IN_PROGRESS` $\to$ `BLOCKED` $\to$ `DONE` $\to$ `TODO`).
  - Lateral Column Shift: `H`/`L` (or `Shift+H`/`Shift+L`) shifts the active card across Kanban columns and syncs focus immediately.
  - Quick Actions: `1-4` priority assignment, `Enter` inline title rename, `d`/`Backspace` deletion, `c` new task modal, `/` filter search.
- **URD-FR-03 [Global Escape Dismissal]**: The `Escape` key shall intercept in capture-phase priority to dismiss any active modal dialog, close dropdown menus, cancel inline editing, and blur active inputs without event swallowing.
- **URD-FR-04 [Local-First Persistence]**: The system shall persist all task mutations instantly to client-side IndexedDB (`idb-keyval`) with synchronous in-memory state caching.
- **URD-FR-05 [Solid Contrast & Anti-Flashbang]**: The system shall enforce solid, non-transparent background surfaces (`bg-slate-100`/`bg-slate-200` light, `bg-slate-950` dark; `bg-white` light cards, `bg-slate-900` dark cards) with 0ms instantaneous theme snapping.

### Should Have (AI & Graph Intelligence)
- **URD-FR-06 [Topological DAG Critical Path]**: The system shall compute dependency chains using Kahn's topological sort and highlight critical path bottlenecks with a `Flame` indicator based on complexity points ($S=1, M=2, L=3, XL=5$).
- **URD-FR-07 [AI Task Decomposer]**: The system shall transform unstructured engineering goals into structured, dependency-linked subtasks via Gemini LLM with deterministic heuristic fallback.
- **URD-FR-08 [Weekly Progress Summary]**: The system shall aggregate completed, in-progress, and blocked tasks into structured overview, blocker, and priority cards.
- **URD-FR-09 [Meeting Minutes Generator]**: The system shall extract structured attendees, decisions, key discussion points, and auto-generable action items from conversational transcripts.
- **URD-FR-10 [Team Workload & Smart Assignment]**: The system shall analyze skill profiles and active WIP loads across team members to recommend the optimal assignee.
- **URD-FR-11 [Git Diff Ticket Synchronizer]**: The system shall parse Unified Git Diffs, detect ticket references (e.g., `resolve #TSK-101`), and update task statuses automatically.

### Could Have (Import / Export & Touch)
- **URD-FR-12 [Lossless JSON Schema Port]**: The system shall export and import the complete task database as formatted JSON.
- **URD-FR-13 [Mobile Touch Ergonomics]**: The system shall support swipe-to-action gestures (swipe right to mark DONE, swipe left to mark BLOCKED) and a docked thumb-zone action bar.

---

# ------------------------------------------------------------------------------
# 2. SYSTEM REQUIREMENTS SPECIFICATION (SRS)
# ------------------------------------------------------------------------------
# Standard: ISO/IEC/IEEE 29148:2018
# Product: Koshi (輿) Project Management System
# Version: 2.0.0 (Vue 3 / FastAPI Architecture)

## 2.1 System Architecture

```text
+-----------------------------------------------------------------------------------+
|                           KOSHI UI Client (Vue 3 + Vite)                          |
|  - Pinia Reactive Store (taskStore, themeStore)                                    |
|  - Spatial Vim Navigation Engine (keyboard.ts)                                     |
|  - High-Density Table (TaskTable.vue) & 2D Kanban (KanbanBoard.vue)                |
|  - Modals: TaskDecomposer, WeeklySummary, MeetingMinutes, WorkloadAssign, GitDiff  |
+------------------------------------------+----------------------------------------+
                                           |
                                  REST API / JSON (Axios)
                                           |
+------------------------------------------v----------------------------------------+
|                          KOSHI Backend Service (FastAPI)                          |
|  - Routers: Auth (OAuth2/JWT), Tasks, Projects, AI Services                       |
|  - AI Engine: Google Gemini 1.5 Pro / Flash + Deterministic Heuristic Fallback    |
|  - Graph Engine: Kahn's Algorithm & Critical Path Matrix                          |
+------------------------------------------+----------------------------------------+
                                           |
                                      SQLAlchemy 2.0
                                           |
+------------------------------------------v----------------------------------------+
|                             SQLite / PostgreSQL Database                          |
+-----------------------------------------------------------------------------------+
```

## 2.2 Functional Requirements (SRS-FR)

### Module 1: State Machine & Task Management
- **SRS-FR-01 [Task Entity Schema]**: Each task entity shall contain:
  - `id`: Unique string identifier (`TSK-[0-9]+`).
  - `title`: String (1-255 characters).
  - `description`: Optional text string.
  - `status`: Enum (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`).
  - `priority`: Enum (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - `complexity`: Enum (`S`, `M`, `L`, `XL`) mapped to points (1, 2, 3, 5).
  - `assignee`: String username reference.
  - `dueDate`: ISO 8601 string or null.
  - `blockingReason`: String explanation when `status === 'BLOCKED'`.
  - `dependencies`: Array of parent task IDs (`TSK-X`).
  - `acceptanceCriteria`: Array of completion conditions.
  - `createdAt`, `updatedAt`: Millisecond timestamps.

- **SRS-FR-02 [Cyclic Status Invariant]**: Invoking status mutation (`cycleStatus`) must strictly follow the modulo-wrapped transition cycle:
  $$\text{TODO} \longrightarrow \text{IN\_PROGRESS} \longrightarrow \text{BLOCKED} \longrightarrow \text{DONE} \longrightarrow \text{TODO}$$

- **SRS-FR-03 [Focus Synchronization]**: Upon any task status shift (via `Space`, `H`/`L`, drag-and-drop, or quick buttons), the store shall invoke `syncKanbanFocusToTask(taskId)` using Vue's `nextTick`, updating `kanbanColIndex` and `kanbanRowIndex` to follow the card.

### Module 2: Table & Kanban Layout Engines
- **SRS-FR-04 [Zero-Jitter Table Rows]**: Table rows in `TaskTable.vue` shall maintain a constant `border-l-2` (`border-l-transparent` when inactive, `border-l-indigo-600 dark:border-l-indigo-400` when active) to eliminate 2px layout jitter.
- **SRS-FR-05 [Completed Task Contrast]**: Completed tasks (`status === 'DONE'`) shall render with `line-through text-slate-500 dark:text-slate-400 font-normal` without applying root opacity filters (`opacity-50`).
- **SRS-FR-06 [Kanban Inset Selection Ring]**: Active Kanban cards shall render selection styling using `ring-2 ring-inset ring-indigo-500 dark:ring-indigo-400 border-indigo-500 dark:border-indigo-400 bg-slate-50 dark:bg-slate-800/90` with zero outward gap.

### Module 3: AI Services & Heuristic Cascades
- **SRS-FR-07 [Gemini API Proxy with Fallback]**: All AI endpoints (`/api/ai/decompose`, `/api/ai/summary`, `/api/ai/minutes`, `/api/ai/workload`) shall query the Gemini LLM API when configured, falling back to deterministic local rule engines if offline or unauthenticated:
  - **Summary**: Aggregates tasks by status with automated blocker flagging.
  - **Minutes**: Regex-based speaker extraction and action item mapping.
  - **Workload**: Heuristic scoring based on skill matching, current active WIP count, and complexity points.

### Module 4: Graph Theory & Dependency Analysis
- **SRS-FR-08 [Topological Sort & Cycle Detection]**: `dagSorter.ts` shall construct a directed graph from `dependencies` and execute Kahn's algorithm. If in-degree reduction fails to process all nodes, a cycle error is reported.
- **SRS-FR-09 [Critical Path Evaluation]**: The critical path is determined by calculating the longest cumulative complexity weight path from root nodes to leaf nodes.

## 2.3 Non-Functional Requirements (SRS-NFR)

- **SRS-NFR-01 [Latency Budget]**: Local mutations (status toggle, selection shift, inline edit) must render in $< 16\text{ms}$ (60fps frame budget).
- **SRS-NFR-02 [Theme Switching]**: DOM `.dark` class mutation must execute in 0ms without transition interpolation on layout wrappers.
- **SRS-NFR-03 [Memory Footprint]**: Frontend runtime footprint must remain $< 25\text{MB}$ heap during continuous operation.
- **SRS-NFR-04 [Viewport Boundaries]**: Docked full-viewport layout (`h-screen overflow-hidden`) with a centered max-width bounds of `1720px` for ultrawide / 4K displays.
