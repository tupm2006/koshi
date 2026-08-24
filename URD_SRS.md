# ==============================================================================
# KOSHI (輿): USER REQUIREMENTS DOCUMENT (URD) & SYSTEM REQUIREMENTS SPECIFICATION (SRS)
# ==============================================================================
# Standard: ISO/IEC/IEEE 29148:2018 Systems and Software Engineering — Requirements Engineering
# System: Koshi Project Management Engine
# Target Deployment: https://koshi.felixsu.qzz.io
# Author: Felix Anderson (felixsu)
# Architecture: Vue 3 (Composition API / Pinia / TypeScript) + FastAPI (Python 3.11 / SQLite / SQLAlchemy)
# Document Version: 2.1.0
# Date: August 24, 2026
# ==============================================================================

---

# 1. USER REQUIREMENTS DOCUMENT (URD)

## 1.1 Purpose, Business Context & Scope
* **Purpose**: This document establishes the formal user, operational, and environmental requirements for Koshi (輿), a high-density, keyboard-driven project management system engineered for technical software teams.
* **Business Context**: Enterprise project trackers introduce significant latency overhead, fragmented navigation hierarchies, and high cognitive load through bloated form modals and nested views. Koshi provides an agile, low-latency, modal-less workspace with local-first offline resilience and integrated AI workflow assistance.
* **Operational Scope**:
  * Dual-mode workspace: High-density Table View and 2D Matrix Kanban Board.
  * Modal-less Vim keyboard navigation protocol (`h/j/k/l`, `Space`, `H/L`, `1-4`, `Enter`, `d`, `/`, `b`, `c`).
  * Capture-phase global `Escape` dismissal architecture.
  * Topological DAG dependency management and Critical Path Method (CPM) calculation.
  * Three integrated AI project management workflows: Weekly Progress Summary, Meeting Minutes Generator, and Team Workload Balancer.
  * Local-first persistence via client-side IndexedDB with background SQLite REST API synchronization.

## 1.2 User Personas & Operational Profiles

### Persona 1: System Architect / Core Engineer
* **Operational Profile**: Works primarily within terminal and tiling window manager environments. Demands continuous keyboard interaction without mouse context switches.
* **Primary Pain Points**: Sluggish UI animations, multi-click status transitions, modal-trapped forms, and lack of dependency visibility.
* **Key Needs**: Sub-16ms UI updates, Vim-style spatial traversal, circular status cycling, and automated critical path identification.

### Persona 2: Project Manager / Tech Lead
* **Operational Profile**: Responsible for sprint velocity, blocker mitigation, meeting synthesis, and equitable workload distribution across team members.
* **Primary Pain Points**: Time lost manually aggregating task statuses for weekly reports, transcribing meeting action items, and calculating developer WIP capacities.
* **Key Needs**: Automated summarization of sprint progress, automated extraction of structured tasks from unstructured meeting transcripts, and skill/capacity-based task assignment recommendations.

### Persona 3: Field / Mobile Developer
* **Operational Profile**: Accesses the board on constrained devices or intermittent networks.
* **Primary Pain Points**: Application failure during network partitions and tiny mobile touch targets.
* **Key Needs**: Local-first offline read/write capability with automatic synchronization upon reconnect, and 44px minimum touch targets with gesture support.

## 1.3 User Requirements Matrix (MoSCoW Classification)

| Requirement ID | Requirement Statement | Priority | Verification Target |
| :--- | :--- | :--- | :--- |
| **URD-FR-01** | The system shall provide instant toggling between a high-density tabular view and a 4-column 2D Kanban board via the `b` shortcut. | **Must Have** | `src/lib/keyboard.ts`, `src/App.vue` |
| **URD-FR-02** | The system shall support modal-less Vim navigation: `j`/`k` (table rows), `h`/`j`/`k`/`l` (2D Kanban grid), `Space` (circular status cycling), and `H`/`L` (lateral column shifting). | **Must Have** | `src/stores/taskStore.ts`, `src/lib/keyboard.ts` |
| **URD-FR-03** | The system shall execute high-priority capture-phase `Escape` handling to dismiss any open modal dialog, cancel inline editing, and blur active inputs. | **Must Have** | `src/App.vue:handleGlobalKeydown` |
| **URD-FR-04** | The system shall execute local-first persistence by immediately committing mutations to client-side IndexedDB before dispatching asynchronous HTTP requests. | **Must Have** | `src/stores/taskStore.ts`, `idb-keyval` |
| **URD-FR-05** | The system shall maintain solid, non-transparent surface contrast (`bg-slate-100`/`bg-slate-200` light, `bg-slate-950` dark) with 0ms transition-frozen theme snapping. | **Must Have** | `src/stores/themeStore.ts`, `src/app.css` |
| **URD-FR-06** | The system shall compute dependency chains using Kahn's topological sort and highlight bottleneck tasks on the Critical Path with visual indicators. | **Should Have** | `src/lib/dagSorter.ts`, `DAGVisualizerModal.vue` |
| **URD-FR-07** | The system shall generate structured Weekly Progress Summaries (Overview, Blockers, Priorities) from active sprint task states. | **Should Have** | `POST /api/v1/ai/weekly-summary`, `WeeklySummaryModal.vue` |
| **URD-FR-08** | The system shall parse unstructured meeting transcripts into structured action items, assignees, and key decisions. | **Should Have** | `POST /api/v1/ai/meeting-minutes`, `MeetingMinutesModal.vue` |
| **URD-FR-09** | The system shall analyze team member skill sets and current WIP point complexity to recommend optimal task assignees. | **Should Have** | `POST /api/v1/ai/recommend-assignment`, `WorkloadAssignModal.vue` |
| **URD-FR-10** | The system shall parse Unified Git Diffs, extract ticket references (`TSK-X`), and resolve completed tasks automatically. | **Should Have** | `src/lib/gitParser.ts`, `GitDiffModal.vue` |
| **URD-FR-11** | The system shall provide lossless JSON export and import for database state backup and migration. | **Could Have** | `src/stores/taskStore.ts:exportJSON` |
| **URD-FR-12** | The system shall support mobile touch gestures (swipe right to mark DONE, swipe left to mark BLOCKED) and a docked bottom thumb bar. | **Could Have** | `src/components/TaskTable.vue`, `MobileBottomNav.vue` |

---

# 2. SYSTEM REQUIREMENTS SPECIFICATION (SRS)

## 2.1 System Architecture & Data Flow Topology

```text
+-----------------------------------------------------------------------------------------+
|                                    CLIENT SUBSYSTEM                                     |
|  Vue 3.5+ (Composition API) / Vite Bundler / Pinia State Engine / Tailwind CSS v4       |
|                                                                                         |
|  +------------------------+  +------------------------+  +---------------------------+  |
|  |   View Presentation    |  |     State & Storage    |  |    Algorithmic Engines    |  |
|  | - TaskTable.vue        |  | - taskStore.ts         |  | - keyboard.ts (Vim Engine)|  |
|  | - KanbanBoard.vue      |  | - themeStore.ts        |  | - dagSorter.ts (Kahn/CPM) |  |
|  | - Modal Dialogs (x8)   |  | - IndexedDB Storage    |  | - gitParser.ts (Diff AST) |  |
|  +------------------------+  +------------------------+  +---------------------------+  |
+--------------------------------------------+--------------------------------------------+
                                             |
                                 HTTPS / REST API / JSON
                                (Bearer JWT Authentication)
                                             |
+--------------------------------------------v--------------------------------------------+
|                                SERVER SUBSYSTEM (Host: umi)                             |
|  Caddy Edge Proxy -> Docker Bridge Network (koshi-internal) -> Nginx Alpine SPA Proxy   |
|                                                                                         |
|  +-----------------------------------------------------------------------------------+  |
|  |                          FastAPI Application Core (Python 3.11)                   |  |
|  |  - Routers: auth.py, tasks.py, projects.py, sprints.py, stats.py, ai.py           |  |
|  |  - Security: JWT HS256 Token Engine, Passlib Bcrypt Hashing, RBAC Middleware      |  |
|  |  - AI Cascade Service: OpenAI API / Local Ollama / Deterministic Fallback Engine  |  |
|  |  - ORM Layer: SQLAlchemy 2.0 Core                                                 |  |
|  +-----------------------------------------+-----------------------------------------+  |
|                                            |                                            |
|                                  SQLite Database Engine                                 |
|                                (Volume: /app/data/koshi.db)                             |
+-----------------------------------------------------------------------------------------+
```

## 2.2 Data Entities & Schema Invariants

### 2.2.1 Entity Relational Definitions
1. **User Entity**:
   * `id`: Integer primary key (Autoincrement).
   * `email`: String(255), Unique, Indexed, Non-nullable.
   * `hashed_password`: String(255), Non-nullable (Bcrypt salted hash).
   * `full_name`: String(255), Non-nullable.
   * `role`: Enum(`RoleEnum.PM`, `RoleEnum.MEMBER`), Default `MEMBER`.
   * `skills`: String(500), Comma-delimited skill tokens (e.g., `"python,fastapi,vue"`).
   * `created_at`: DateTime (UTC ISO 8601).

2. **Task Entity**:
   * `id`: String(32), Primary key (Format: `TSK-[0-9]+`).
   * `project_id`: Integer, Foreign Key referencing `projects.id`.
   * `sprint_id`: Optional Integer, Foreign Key referencing `sprints.id`.
   * `assignee_id`: Optional Integer, Foreign Key referencing `users.id`.
   * `title`: String(255), Non-nullable.
   * `description`: Optional Text.
   * `status`: Enum(`TaskStatusEnum.TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`).
   * `priority`: Enum(`TaskPriorityEnum.LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
   * `complexity_points`: Integer, Mapping: $S \to 1, M \to 2, L \to 3, XL \to 5$.
   * `due_date`: Optional DateTime.
   * `blocking_reason`: Optional String(500) (Mandatory when `status == BLOCKED`).
   * `created_at`, `updated_at`: DateTime (UTC ISO 8601).

3. **Task Dependency Entity**:
   * `id`: Integer primary key.
   * `task_id`: String(32), Foreign key referencing dependent `tasks.id`.
   * `depends_on_task_id`: String(32), Foreign key referencing prerequisite `tasks.id`.

### 2.2.2 Mathematical State Transition Invariants
Let $S$ denote the ordered sequence of task states:
$$S = \langle \text{TODO}, \text{IN\_PROGRESS}, \text{BLOCKED}, \text{DONE} \rangle, \quad |S| = 4$$

The circular status mutation function $f: S \to S$ is defined by:
$$f(S_i) = S_{(i + 1) \pmod 4}$$

Upon execution of $f(S_i)$, the client synchronously executes focus relocation:
$$\text{syncKanbanFocusToTask}(t_{\text{id}}) \implies \begin{cases}
c_{\text{idx}} = \text{index\_of}(t.\text{status}) \\
r_{\text{idx}} = \text{find\_index}(C_{c_{\text{idx}}}, t_{\text{id}})
\end{cases}$$
where $C_{c_{\text{idx}}}$ represents the ordered subset of tasks belonging to column $c_{\text{idx}}$.

## 2.3 Functional Requirements by Subsystem (SRS-FR)

### Subsystem 1: Interaction, Traversal & Focus Engine
* **SRS-FR-01 [Vim Navigation Router]**:
  * In Table View: `j`/`k` increment/decrement `taskStore.selectedIndex` bounded in $[0, N-1]$.
  * In Kanban View: `h`/`l` modify column index $c \in [0, 3]$; `j`/`k` modify row index $r \in [0, |C_c|-1]$.
  * Lateral Shift: `Shift+H` / `Shift+L` shifts the active task left/right across columns and preserves active focus on the mutated task.
* **SRS-FR-02 [Input-Focus Guards]**: Single-key hotkeys evaluate `!isInputActive()` prior to dispatch, preventing action triggers while focused in `<input>`, `<textarea>`, or `contenteditable` nodes.
* **SRS-FR-03 [Capture-Phase Global Escape]**: The application root (`src/App.vue`) binds an `Escape` keydown listener in the capture phase (`addEventListener('keydown', handler, true)`), guaranteeing instant dismissal of all open modals, dropdown menus, inline edit states, and search focus without event swallowing.

### Subsystem 2: Layout, Theming & Visual Surface Invariants
* **SRS-FR-04 [Zero-Jitter Table Alignment]**: Table rows in `TaskTable.vue` maintain a permanent `border-l-2` (`border-l-transparent` when inactive, `border-l-indigo-600 dark:border-l-indigo-400` when selected), preventing horizontal pixel displacement on active row traversal.
* **SRS-FR-05 [Completed Task Contrast Standard]**: Tasks in `DONE` status render with `line-through text-slate-500 dark:text-slate-400` without root `opacity-50` modifiers, maintaining WCAG AA minimum contrast ratio ($\ge 4.5:1$).
* **SRS-FR-06 [Kanban Inset Selection Bounds]**: Active Kanban card selection uses `ring-2 ring-inset ring-indigo-500 dark:ring-indigo-400` to eliminate visual ring-offset gaps in dark mode.
* **SRS-FR-07 [Zero-FOUC & 0ms Transition Freeze]**: Theme state initializes via a synchronous `<head>` evaluation script. Theme toggling (`themeStore.toggleTheme()`) injects a temporary `* { transition: none !important; }` style element during `.dark` class mutation to guarantee 0ms instant snapping.

### Subsystem 3: Graph Engine & Critical Path Method (CPM)
* **SRS-FR-08 [Topological Sort & Cycle Detection]**:
  * Given directed graph $G = (V, E)$, Kahn's algorithm computes in-degree $\text{deg}^-(v)$ for all $v \in V$.
  * Nodes with $\text{deg}^-(v) = 0$ are enqueued into set $L$.
  * If $|L| < |V|$ upon termination, the engine rejects the graph with a circular dependency fault (`CycleDetectedException`).
* **SRS-FR-09 [Critical Path Longest-Path Solver]**:
  * Earliest Start ($ES$) and Earliest Finish ($EF$) times are evaluated forward:
    $$ES(v) = \max_{(u, v) \in E} EF(u), \quad EF(v) = ES(v) + W(v)$$
    where $W(v)$ is the task's complexity weight ($S=1, M=2, L=3, XL=5$).
  * Tasks on the maximal duration path from root to terminal leaf are assigned the `Flame` Critical Path indicator.

### Subsystem 4: AI Workflow Services & Multi-Tier Cascade
* **SRS-FR-10 [Cascading AI Service Architecture]**:
  All AI endpoints implement three-tier cascading execution:
  $$\text{Tier 1: OpenAI/External LLM API} \longrightarrow \text{Tier 2: Local Ollama Endpoint} \longrightarrow \text{Tier 3: Deterministic Rule Parser}$$
* **SRS-FR-11 [Weekly Progress Summary API]**: `POST /api/v1/ai/weekly-summary` aggregates sprint tasks and produces structured sections (Overview, Active Blockers, Priorities).
* **SRS-FR-12 [Meeting Minutes Extraction API]**: `POST /api/v1/ai/meeting-minutes` parses raw conversational transcripts and returns structured JSON arrays of `main_topics`, `action_items` (title, assignee, priority, deadline), and `key_decisions`.
* **SRS-FR-13 [Workload Balancing & Assignment API]**: `POST /api/v1/ai/recommend-assignment` computes member assignment recommendations by minimizing the cost function:
  $$J(u) = \alpha \cdot \text{WIP}(u) + \beta \cdot \text{Pts}(u) - \gamma \cdot \text{SkillMatch}(u, \text{Task})$$

## 2.4 Non-Functional Requirements (SRS-NFR)

* **SRS-NFR-01 [Frame Budget & Render Latency]**: Local mutations (status toggle, row selection, priority change) must commit to the DOM within $< 16\text{ms}$ ($60\text{ fps}$).
* **SRS-NFR-02 [Network Telemetry Model]**: Production UI must adhere to the "Silence is Success" rule. Background synchronization remains silent during normal operation and displays an amber pulsing warning badge (`Offline (Local buffer)`) strictly when backend connectivity fails.
* **SRS-NFR-03 [Widescreen Layout Bounds]**: Application shell must dock to `h-screen overflow-hidden` with a centered max-width constraint of `1720px` to prevent layout disintegration on 4K/Ultrawide displays.
* **SRS-NFR-04 [Security & Role Barriers]**: All `/api/v1/` routes (excluding auth and health) require a valid JWT Bearer token with signature verification (`HS256`). Sprint creation and project reconfiguration require `RoleEnum.PM`.

---

# 3. REQUIREMENTS TRACEABILITY & VERIFICATION MATRIX

| User Req ID | SRS Spec ID | Subsystem / Component | Implementation File | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **URD-FR-01** | SRS-FR-01 | View Switcher | `src/lib/keyboard.ts`, `src/App.vue` | Manual UI Test (`b` hotkey) |
| **URD-FR-02** | SRS-FR-01 | Vim Navigation | `src/lib/keyboard.ts`, `src/stores/taskStore.ts` | Manual / Playwright E2E |
| **URD-FR-03** | SRS-FR-03 | Global Escape | `src/App.vue` | Manual UI Test (`Escape` capture) |
| **URD-FR-04** | SRS-FR-01 | Client Persistence | `src/stores/taskStore.ts` | LocalStorage / IDB Inspection |
| **URD-FR-05** | SRS-FR-07 | Theming Engine | `src/stores/themeStore.ts`, `index.html` | Visual Regression / DOM Audit |
| **URD-FR-06** | SRS-FR-08, 09 | Graph Engine | `src/lib/dagSorter.ts`, `backend/app/routers/tasks.py` | Automated Pytest (`test_tasks.py`) |
| **URD-FR-07** | SRS-FR-11 | AI Summary | `backend/app/routers/ai.py`, `WeeklySummaryModal.vue` | Automated Pytest (`test_ai_and_stats.py`) |
| **URD-FR-08** | SRS-FR-12 | AI Minutes | `backend/app/routers/ai.py`, `MeetingMinutesModal.vue` | Automated Pytest (`test_ai_and_stats.py`) |
| **URD-FR-09** | SRS-FR-13 | AI Workload | `backend/app/routers/ai.py`, `WorkloadAssignModal.vue` | Automated Pytest (`test_ai_and_stats.py`) |
| **URD-FR-10** | SRS-FR-01 | Git Diff Parser | `src/lib/gitParser.ts`, `GitDiffModal.vue` | Unit Test (`gitParser.test.ts`) |
| **URD-FR-11** | SRS-FR-01 | JSON Backup | `src/stores/taskStore.ts` | Unit Test (Schema validation) |
| **URD-FR-12** | SRS-FR-01 | Mobile Touch | `src/components/TaskTable.vue`, `MobileBottomNav.vue` | Mobile Viewport Emulation |
