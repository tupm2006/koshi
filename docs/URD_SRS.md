# ==============================================================================
# KOSHI (輿): USER REQUIREMENTS DOCUMENT (URD) & SYSTEM REQUIREMENTS SPECIFICATION (SRS)
# ==============================================================================
# Standard: ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering
# System Identifier: KOSHI-PMS-2.0
# Production Deployment: https://koshi.felixsu.qzz.io
# Author / Maintainer: Felix Su (felixsu) <me@felixsu.qzz.io>
# Target Architecture: Vue 3 (Composition API / Pinia / TypeScript / Tailwind CSS v4) + FastAPI (Python 3.11 / SQLAlchemy 2.0 / SQLite / JWT RBAC)
# ==============================================================================

---

# SECTION 1: USER REQUIREMENTS DOCUMENT (URD)

## 1.1 Scope & Executive Problem Statement

Enterprise issue trackers and project management platforms (e.g., Atlassian Jira, Linear, ClickUp) suffer from severe architectural regressions that compromise developer velocity:
1. **High Cognitive Latency & Bloated Runtimes**: Pervasive virtual DOM diffing, multi-megabyte bundle payloads, and 800MB–2GB Electron memory footprints cause UI stutter and action execution latencies exceeding 1500ms.
2. **Pointer-Dominated CRUD Inefficiency**: Routine status changes, title renames, and priority updates force context switches from the keyboard to precise mouse targeting across nested dialog hierarchies.
3. **Fragile Network Coupled State**: Traditional Single-Page Applications (SPAs) degrade immediately upon intermittent network drops, resulting in lost mutation buffers and broken workflow pipelines.

**Koshi (輿)** is a deterministic, local-first project management system engineered to eliminate interaction friction through 2D spatial Vim traversal, modulo-wrapped state transitions, topological critical path computation, and offline-first IndexedDB persistence backed by a lightweight FastAPI server.

---

## 1.2 User Personas & Operational Profiles

### Persona 1: System Architect & Core Engineer (`ENG-ARCH`)
- **Operational Context**: High-throughput terminal and IDE-centric development.
- **Pain Points**: Friction from clicking multi-tier dropdowns, lack of rapid keyboard traversal, inability to inspect true graph bottlenecks.
- **Needs**: Sub-16ms render loop, modal-less 2D Vim navigation (`h/j/k/l`, `Space`, `H/L`, `1-4`, `Enter`), and instant DAG critical path isolation.

### Persona 2: Project Manager & Tech Lead (`PM-LEAD`)
- **Operational Context**: Sprint planning, capacity balancing, and meeting synthesis.
- **Pain Points**: Manual compilation of status updates across fragmented tickets, subjective capacity estimates, unformatted meeting notes.
- **Needs**: Automated weekly status/blocker aggregation, transcript-to-action-item extraction, and deterministic workload allocation recommendations based on skill and active WIP load.

### Persona 3: Field & Mobile Developer (`MOB-DEV`)
- **Operational Context**: Unstable mobile networks, on-call deployments, tablet/phone review.
- **Pain Points**: Network timeout errors during state mutations, cramped desktop-only layouts.
- **Needs**: Local-first offline write buffers via IndexedDB with automatic background synchronization and tactile swipe-to-action gestures.

---

## 1.3 User Requirements Matrix (MoSCoW Classification)

| Requirement ID | Category | Description | Priority |
| :--- | :--- | :--- | :--- |
| **URD-FR-01** | Dual-Mode Presentation | The system shall provide instant single-key toggling (`b`) between a high-density Table Grid and a 4-column 2D Kanban Board. | **Must Have** |
| **URD-FR-02** | 2D Vim Keyboard Ergonomics | The system shall provide modal-less keyboard navigation: `j`/`k` vertical traversal, `h`/`l` horizontal column traversal, `Space` cyclic status rotation, `H`/`L` lateral column shifts, `Enter` inline edit, `1-4` priority assign, `d` delete, and `/` filter search. | **Must Have** |
| **URD-FR-03** | Capture-Phase Escape Dismissal | The `Escape` key shall intercept with top priority at the window capture phase to dismiss any open modal, close menus, cancel inline edits, and blur active inputs. | **Must Have** |
| **URD-FR-04** | Solid Contrast & Anti-Flashbang | The UI shall enforce solid floor neutrals (`bg-slate-100`/`bg-slate-200` light, `bg-slate-950` dark) and elevated cards (`bg-white` light, `bg-slate-900` dark) with 0ms transition-frozen theme snaps. | **Must Have** |
| **URD-FR-05** | Local-First Offline Persistence | The system shall persist all task mutations synchronously in memory and asynchronously to client IndexedDB storage (`idb-keyval`), permitting uninterrupted offline operation. | **Must Have** |
| **URD-FR-06** | Topological DAG Critical Path | The system shall compute dependency chains using Kahn's topological sort and flag critical path bottleneck tasks with a `Flame` indicator. | **Should Have** |
| **URD-FR-07** | Automated Task Decomposition | The system shall compile unstructured engineering goals into structured, dependency-linked subtask graphs with complexity ratings via a multi-tier AI cascade. | **Should Have** |
| **URD-FR-08** | Weekly Progress Summary | The system shall aggregate completed milestones, active bottlenecks, and immediate sprint priorities into structured executive cards. | **Should Have** |
| **URD-FR-09** | Meeting Minutes Synthesis | The system shall parse conversational meeting transcripts to extract attendees, recorded decisions, key discussions, and auto-generated actionable tasks. | **Should Have** |
| **URD-FR-10** | Team Workload Balancing | The system shall analyze team member skill affinities and active WIP load to recommend optimal task assignees. | **Should Have** |
| **URD-FR-11** | Git Diff State Sync | The system shall parse Unified Git Diffs and commit logs to extract ticket references (e.g., `resolve #TSK-101`) and update task states automatically. | **Should Have** |
| **URD-FR-12** | Lossless JSON Port & Mobile Touch | The system shall support full JSON schema database import/export and mobile swipe gestures (swipe right for DONE, swipe left for BLOCKED). | **Could Have** |

---

# SECTION 2: SYSTEM REQUIREMENTS SPECIFICATION (SRS)

## 2.1 System Architecture & Data Flow Topology

```text
+---------------------------------------------------------------------------------------------------+
|                                      CLIENT RUNTIME (Browser)                                     |
|                                                                                                   |
|  +-----------------------------------+   +-----------------------------------------------------+  |
|  |       Pinia Reactive Stores       |   |             Vim Keyboard Dispatcher                 |  |
|  | - taskStore.ts (State & Mutators) |<--| - keyboard.ts (Capture-Phase Listeners, Input Guard)|  |
|  | - themeStore.ts (0ms Theme Snap)  |   +-----------------------------------------------------+  |
|  +-----------------+-----------------+                                                             |
|                    |                                                                              |
|                    v                                                                              |
|  +---------------------------------------------------------------------------------------------+  |
|  |                                  Vue 3 Component Tree                                       |  |
|  | - App.vue (Docked 100dvh Layout, 1720px Centered Canvas, AI Menu Dropdown, Modal Router)    |  |
|  | - TaskTable.vue (Constant border-l-2 Rows, Solid Strikethrough DONE Contrast)               |  |
|  | - KanbanBoard.vue (Natural Top Clustering, ring-2 ring-inset Active Card Focus)             |  |
|  | - Modals: AIDecomposer, WeeklySummary, MeetingMinutes, WorkloadAssign, GitDiff, DAGVisual   |  |
|  +-----------------+---------------------------------------------------------------------------+  |
|                    |                                                                              |
|          +---------v---------+                             +-------------------------+            |
|          | Client Persistence|                             |    REST Client (Axios)  |            |
|          | - idb-keyval      |<----------------------------| - src/services/api.ts   |            |
|          | - IndexedDB       |                             +------------+------------+            |
|          +-------------------+                                          |                         |
+-------------------------------------------------------------------------|-------------------------+
                                                                          | HTTPS / JSON
                                                                          v
+---------------------------------------------------------------------------------------------------+
|                                      HOST SYSTEM: umi (Docker Engine)                             |
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  |                                  Caddy Reverse Proxy (:443)                                 |  |
|  |                      TLS Termination • Automatic Let's Encrypt Certificates                 |  |
|  +--------------------+---------------------------------------------------+--------------------+  |
|                       | /                                                 | /api                  |
|                       v                                                   v                       |
|  +-----------------------------------------+     +---------------------------------------------+  |
|  | Container: koshi (Frontend Nginx :80)   |     | Container: koshi-backend (Uvicorn :8000)    |  |
|  | - Static Production SPA Assets          |     | - FastAPI Routing & OAuth2 JWT RBAC Engine  |  |
|  | - Custom Nginx Fallback Routing         |     | - Pydantic Request Validation               |  |
|  +-----------------------------------------+     +----------------------+----------------------+  |
|                                                                         |                         |
|                                                  +----------------------+----------------------+  |
|                                                  |                                             |  |
|                                                  v                                             v  |
|                                   +----------------------------+                 +-------------+  |
|                                   | SQLAlchemy 2.0 ORM Engine  |                 |  AI Engine  |  |
|                                   | - SQLite Database File     |                 |  - Gemini   |  |
|                                   | - SQLite WAL Persistent Vol|                 |  - Heuristic|  |
|                                   +----------------------------+                 +-------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2.2 Data Entity Dictionary & Schema Invariants

### 2.2.1 Core Domain Entities

```text
+---------------------+          +-----------------------+          +-------------------------+
|        User         |          |        Project        |          |          Sprint         |
+---------------------+          +-----------------------+          +-------------------------+
| id: int (PK)        |<---+     | id: int (PK)          |<---+     | id: int (PK)            |
| username: str (UQ)  |    |     | name: str             |    +-----| project_id: int (FK)    |
| email: str (UQ)     |    |     | key: str (UQ)         |          | name: str               |
| hashed_password: str|    |     | description: str      |          | start_date: datetime    |
| role: RoleEnum      |    |     | owner_id: int (FK)----+          | end_date: datetime      |
| skills: str (CSV)   |    |     | created_at: datetime  |          | is_active: bool         |
| created_at: datetime|    |     +-----------------------+          +-------------------------+
+---------------------+    |                 |                                   |
         |                 |                 | 1:N                               | 1:N
         | 1:N             |                 v                                   v
         |                 |     +------------------------------------------------------------+
         |                 |     |                            Task                            |
         |                 |     +------------------------------------------------------------+
         |                 |     | id: int (PK)                                               |
         |                 |     | project_id: int (FK)                                       |
         |                 |     | sprint_id: int (FK, Nullable)                              |
         |                 +-----| assignee_id: int (FK, Nullable)                            |
         |                       | title: str (1..255)                                        |
         |                       | description: str (Nullable)                                |
         |                       | status: TaskStatus (TODO | IN_PROGRESS | BLOCKED | DONE)   |
         |                       | priority: TaskPriority (LOW | MEDIUM | HIGH | CRITICAL)    |
         |                       | complexity_points: int (1, 2, 3, 5)                        |
         |                       | due_date: datetime (Nullable)                              |
         |                       | blocking_reason: str (Nullable)                            |
         |                       | dependencies: list[str] (JSON Array of Task IDs)           |
         |                       | acceptance_criteria: list[str] (JSON Array of Strings)     |
         |                       | created_at: datetime                                       |
         |                       | updated_at: datetime                                       |
         |                       +------------------------------------------------------------+
         |                                                     | 1:N
         |                                                     v
         |                       +------------------------------------------------------------+
         |                       |                           Comment                          |
         |                       +------------------------------------------------------------+
         |                       | id: int (PK)                                               |
         +-----------------------| user_id: int (FK)                                          |
                                 | task_id: int (FK)                                          |
                                 | content: str                                               |
                                 | created_at: datetime                                       |
                                 +------------------------------------------------------------+
```

### 2.2.2 Exact Type & Enum Specifications

```typescript
export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'DONE';
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Complexity = 'S' | 'M' | 'L' | 'XL';

export interface Task {
  id: string;                      // Format: "TSK-101"
  title: string;                   // 1..255 characters
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  complexity: Complexity;          // S=1, M=2, L=3, XL=5 points
  assignee?: string;               // Username reference
  dueDate?: string;                // ISO 8601 string
  blockingReason?: string;         // Mandatory when status === 'BLOCKED'
  dependencies: string[];          // Array of parent task IDs
  acceptanceCriteria: string[];    // Array of string conditions
  createdAt: number;               // Milliseconds epoch
  updatedAt: number;               // Milliseconds epoch
}
```

---

## 2.3 State Machine & Cyclic Transition Invariants

### 2.3.1 Modulo State Rotation
Let the set of task statuses be ordered as an indexed sequence $S = \langle s_0, s_1, s_2, s_3 \rangle$:
$$S = \langle \text{TODO}, \text{IN\_PROGRESS}, \text{BLOCKED}, \text{DONE} \rangle$$

The state transition function $\delta: S \to S$ executed upon pressing `Space` or invoking status cycle is defined by:
$$\delta(s_i) = S[(i + 1) \pmod 4]$$

The bidirectional column shift function $\sigma: S \times \{ -1, 1 \} \to S$ executed upon pressing `H` or `L` is defined by:
$$\sigma(s_i, \Delta) = S[(i + \Delta + 4) \pmod 4]$$

```text
       +------------------ Space / L ------------------+
       |                                               |
       v                                               |
  +----------+     Space / L     +---------------+     |
  |   TODO   | ----------------> |  IN_PROGRESS  |     |
  +----------+                   +---------------+     |
       ^                                 |             |
       | H                             Space / L       |
       |                                 v             |
  +----------+     Space / L     +---------------+     |
  |   DONE   | <---------------- |    BLOCKED    |     |
  +----------+                   +---------------+     |
       |                                               |
       +---------------------- H ----------------------+
```

### 2.3.2 Focus Synchronization Protocol
Whenever a task $T$ with identifier $T_{id}$ undergoes a state mutation $s_{old} \to s_{new}$:
1. The store mutates the in-memory array and updates IndexedDB.
2. The store evaluates the new column index:
   $$c_{target} = \text{indexOf}(S, s_{new})$$
3. The store queries the column's task subset $C = \{ t \in \text{tasks} \mid t.\text{status} = s_{new} \}$.
4. The store identifies the row position $r_{target} = \text{indexOf}(C, T_{id})$.
5. Inside Vue's `nextTick()`, the active focus matrix updates:
   $$\text{kanbanColIndex} \leftarrow c_{target}, \quad \text{kanbanRowIndex} \leftarrow \max(0, r_{target})$$

---

## 2.4 Functional Requirements by Module (SRS-FR)

### Module 1: Navigation & Interaction Engine
- **SRS-FR-01 [Keyboard Input Guard]**: Global keydown listeners shall inspect `event.target`. If `isInputActive(target)` is true (`INPUT`, `TEXTAREA`, `SELECT`, `contentEditable`), single-key dispatchers (`j`, `k`, `h`, `l`, `Space`, `1-4`, `d`, `c`, `/`) must yield to standard text entry.
- **SRS-FR-02 [Capture-Phase Escape Intercept]**: The window keydown listener for `Escape` shall attach in the capture phase (`addEventListener('keydown', fn, true)`). It shall invoke `closeAllModals()` to close any open modal dialogs, close the AI header menu, terminate inline table editing via `stopEditing()`, and blur focused search inputs.
- **SRS-FR-03 [2D Kanban Spatial Navigation]**:
  - `h` / `ArrowLeft`: $\text{kanbanColIndex} \leftarrow \max(0, \text{kanbanColIndex} - 1)$.
  - `l` / `ArrowRight`: $\text{kanbanColIndex} \leftarrow \min(3, \text{kanbanColIndex} + 1)$.
  - `k` / `ArrowUp`: $\text{kanbanRowIndex} \leftarrow \max(0, \text{kanbanRowIndex} - 1)$.
  - `j` / `ArrowDown`: $\text{kanbanRowIndex} \leftarrow \min(|C| - 1, \text{kanbanRowIndex} + 1)$.

### Module 2: Layout & Surface Design System
- **SRS-FR-04 [Zero-Jitter Table Row Boundary]**: Every table row container in `TaskTable.vue` shall maintain a permanent 2px left border:
  - Inactive: `border-l-2 border-l-transparent hover:bg-slate-50 dark:hover:bg-slate-800/60`.
  - Selected: `border-l-2 border-l-indigo-600 dark:border-l-indigo-400 bg-indigo-50/80 dark:bg-slate-800`.
- **SRS-FR-05 [Completed Task Legibility]**: Completed tasks (`status === 'DONE'`) shall render title text using `line-through text-slate-500 dark:text-slate-400 font-normal`. The row container shall NOT apply `opacity-50`.
- **SRS-FR-06 [Kanban Inset Selection Indicator]**: Active Kanban cards shall render selection styling using `ring-2 ring-inset ring-indigo-500 dark:ring-indigo-400 border-indigo-500 dark:border-indigo-400 bg-slate-50 dark:bg-slate-800/90` with zero outward gap.
- **SRS-FR-07 [Full-Viewport Docked Layout]**: The desktop canvas shall lock to `h-screen h-[100dvh] flex flex-col overflow-hidden` with fixed headers (`h-12`), filter toolbars (`h-11`), and footers (`h-9`). The workspace area shall constrain horizontal sprawl to `max-w-[1720px] mx-auto w-full`.

### Module 3: Graph & Critical Path Engine
- **SRS-FR-08 [Kahn's Topological Sorting]**: Given directed graph $G = (V, E)$ where $V = \text{tasks}$ and directed edge $(u, v) \in E$ indicates task $v$ depends on task $u$:
  1. Compute in-degree $d^-(v)$ for all $v \in V$.
  2. Initialize queue $Q \leftarrow \{ v \in V \mid d^-(v) = 0 \}$.
  3. While $Q \neq \emptyset$: dequeue $u$, append $u$ to sorted list $L$; for each edge $(u, v)$, decrement $d^-(v)$; if $d^-(v) = 0$, enqueue $v$.
  4. If $|L| < |V|$, the system shall raise a cycle detection exception.
- **SRS-FR-09 [Critical Path Method (CPM)]**: The engine shall compute the cumulative duration/complexity weight along all paths in the DAG. Tasks belonging to the maximal weight path shall have their IDs stored in `criticalPathIds: Set<string>` and display the `Flame` icon.

### Module 4: Multi-Tier AI Subsystem
- **SRS-FR-10 [Cascading AI Resolver]**: Endpoints (`/ai/weekly-summary`, `/ai/meeting-minutes`, `/ai/recommend-assignment`, `/ai/decompose`) shall execute through a 3-tier cascade:
  1. **Tier 1 (Google Gemini 1.5 API)**: Structured schema query via official SDK.
  2. **Tier 2 (Local Ollama Daemon)**: On HTTP 503/timeout, forward to `http://localhost:11434/api/generate`.
  3. **Tier 3 (Deterministic Heuristic Engines)**: Pure algorithmic fallback:
     - *Summary*: Bucket tasks by status, extract blockers into alert tokens.
     - *Minutes*: Regex speaker pattern matching and action-item generation.
     - *Workload*: Capacity formula $\text{Score}(u) = \text{SkillMatch}(u, \text{tags}) \times 10 - \text{ActiveWIP}(u) \times 2 - \text{Points}(u)$.

---

## 2.5 Non-Functional Requirements (SRS-NFR)

### 2.5.1 Performance & Latency Budgets
- **SRS-NFR-01 [Action Loop Latency]**: Client-side reactive mutations (selection move, status cycle, inline edit open) must execute in $< 16\text{ms}$ (60fps rendering frame budget).
- **SRS-NFR-02 [Theme Toggle Instantaneity]**: DOM `.dark` class mutation must execute in $< 2\text{ms}$ (0ms perceived snap). Global layout transitions on background surfaces are prohibited.
- **SRS-NFR-03 [Memory Overhead]**: Idle web runtime memory must remain $< 25\text{MB}$ heap allocation.

### 2.5.2 Security & Authentication
- **SRS-NFR-04 [JWT RBAC Security]**: Backend API authorization shall enforce RFC 7519 JSON Web Tokens signed with HMAC-SHA256. Passwords must be hashed using `bcrypt` with a minimum work factor of 12.
- **SRS-NFR-05 [Role Enforcement]**: Role-Based Access Control (`RoleEnum.PM` vs `RoleEnum.MEMBER`) shall be verified at the FastAPI router dependency level.

### 2.5.3 Reliability & Local-First Invariants
- **SRS-NFR-06 [Offline Partition Tolerance]**: All local CRUD operations must succeed without network connectivity. Mutated entities are flagged for reconciliation when the `/api/tasks` endpoint resumes availability.
- **SRS-NFR-07 [Clipboard Resiliency]**: In non-HTTPS or permission-restricted environments, clipboard writes must fallback seamlessly to a hidden `textarea` and `document.execCommand('copy')`.

---

# SECTION 3: REQUIREMENTS TRACEABILITY & VERIFICATION MATRIX

| User Req ID | SRS Function ID | Source Component / Implementation Path | Verification Method | Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **URD-FR-01** | SRS-FR-01, SRS-FR-07 | `src/App.vue`, `src/stores/taskStore.ts` | Manual / UI Test | Pressing `b` swaps between Table and Kanban without focus loss. |
| **URD-FR-02** | SRS-FR-01, SRS-FR-03 | `src/lib/keyboard.ts`, `src/stores/taskStore.ts` | Vitest Unit Test | `h/j/k/l`, `Space`, `H/L` update active indices accurately. |
| **URD-FR-03** | SRS-FR-02 | `src/App.vue`, `src/components/*Modal.vue` | Vitest / E2E | `Escape` key closes topmost open overlay and clears edit state. |
| **URD-FR-04** | SRS-FR-06, SRS-NFR-02 | `src/stores/themeStore.ts`, `index.html` | Playwright / Visual | Instant 0ms theme toggle; zero alpha bleach over white backgrounds. |
| **URD-FR-05** | SRS-NFR-06 | `src/stores/taskStore.ts`, `idb-keyval` | Vitest Unit Test | Tasks persist across page reloads in offline browser state. |
| **URD-FR-06** | SRS-FR-08, SRS-FR-09 | `src/lib/dagSorter.ts`, `src/components/DAGVisualizerModal.vue` | Pytest / Vitest | Kahn's algorithm resolves DAG; cycle returns explicit error; CPM flags bottleneck. |
| **URD-FR-07** | SRS-FR-10 | `backend/app/services/ai_service.py`, `src/components/AIDecomposerModal.vue` | Pytest Suite | Endpoint returns structured JSON subtasks with dependency mapping. |
| **URD-FR-08** | SRS-FR-10 | `backend/app/services/ai_service.py`, `src/components/WeeklySummaryModal.vue` | Pytest Suite | Summary categorizes Overview, Blockers, Priorities into clean semantic cards. |
| **URD-FR-09** | SRS-FR-10 | `backend/app/services/ai_service.py`, `src/components/MeetingMinutesModal.vue` | Pytest Suite | Transcript parsed into structured action items with 1-click batch create. |
| **URD-FR-10** | SRS-FR-10 | `backend/app/services/ai_service.py`, `src/components/WorkloadAssignModal.vue` | Pytest Suite | Heuristic scoring recommends optimal developer based on WIP load and skills. |
| **URD-FR-11** | SRS-FR-01 | `src/lib/gitParser.ts`, `src/components/GitDiffModal.vue` | Vitest Unit Test | Unified Git Diff commits auto-link and update task statuses. |
| **URD-FR-12** | SRS-FR-04, SRS-NFR-07 | `src/components/TaskTable.vue`, `src/App.vue` | Manual / UI Test | JSON backup download/upload works; table rows show zero 2px horizontal jitter. |

---

# SECTION 4: REVISION HISTORY

| Version | Date | Author | Description of Changes |
| :--- | :--- | :--- | :--- |
| `1.0.0` | 2026-08-15 | Felix Su | Initial Svelte 5 / IndexedDB single-file specification prototype. |
| `1.5.0` | 2026-08-20 | Felix Su | Integration of FastAPI backend, JWT authentication, and AI services. |
| `2.0.0` | 2026-08-24 | Felix Su | Complete architectural refactor to Vue 3 Composition API & Pinia. Added 2D spatial Vim navigation, modulo-wrapped status transitions, Kahn's DAG evaluator, and ISO/IEC/IEEE 29148:2018 traceability matrix. |
