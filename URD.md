# ==============================================================================
# KOSHI (輿): USER REQUIREMENTS DOCUMENT (URD)
# ==============================================================================
# Standard: ISO/IEC/IEEE 29148:2018 — User Requirements Specification
# System: Koshi Project Management Engine
# Target URL: https://koshi.tupm.qzz.io
# Author: Phạm Minh Tú
# Maintainer & Core Team:
#   - Lead Architect & Developer: Phạm Minh Tú
#   - Contributors: Phạm Văn Huynh, Đàm Đức Đôn
# Version: 2.1.0
# Date: August 24, 2026
# ==============================================================================

## 1. Purpose & Business Objective
Koshi (輿) is a lightweight, local-first, keyboard-driven project management engine engineered for high-velocity software engineering teams. Modern web-based issue trackers suffer from heavy virtual DOM abstraction, network-dependent interaction lag, bloated form dialogs, and cumbersome multi-click status manipulation. 

Koshi resolves these operational bottlenecks by providing:
1. Sub-16ms deterministic UI responses with zero input latency.
2. Full modal-less Vim keyboard navigation for both tabular and spatial Kanban workflows.
3. Offline-first local data ownership via client-side IndexedDB with background REST synchronization.
4. Autonomous PM assistant workflows (progress summarization, meeting minutes extraction, workload balancing) with multi-tier heuristic fallbacks.

---

## 2. User Personas & Operational Profiles

### 2.1 Persona 1: System Architect / Core Engineer
* **Operational Context**: Operates primarily within tiling window managers, terminal environments, and Neovim. Demands continuous keyboard ergonomics without mouse context switches.
* **Pain Points**: Sluggish UI animations, multi-step modal forms, and lack of dependency visibility.
* **Operational Goals**:
  * Traverse, filter, create, and mutate task states in $< 50\text{ms}$ entirely via keystrokes.
  * Rapidly inspect dependency graphs and identify critical path bottlenecks before merge windows.

### 2.2 Persona 2: Project Manager / Tech Lead
* **Operational Context**: Responsible for sprint velocity, blocker resolution, meeting synthesis, and equitable workload allocation across team members.
* **Pain Points**: Time spent manually transcribing meeting notes, synthesizing status reports, and calculating developer capacity points.
* **Operational Goals**:
  * Automatically convert unstructured meeting transcripts into structured action items with assignees and priorities.
  * Generate instant sprint progress and blocker summaries.
  * Receive data-driven task assignment recommendations based on team member skills and current WIP points.

### 2.3 Persona 3: Field / Offline Developer
* **Operational Context**: Accesses the board on mobile devices or during network partitions.
* **Pain Points**: Complete application lockup or data loss when internet connectivity drops.
* **Operational Goals**:
  * Execute read and write operations seamlessly offline, persisting state locally to IndexedDB.
  * Utilize ergonomic touch swipe gestures on mobile viewports.

---

## 3. User Requirements Matrix (MoSCoW Classification)

### 3.1 Must Have (Core Operational Invariants)
* **URD-FR-01 [Dual-Mode Views]**: The user shall seamlessly toggle between a high-density Table View and a 4-column 2D Kanban Board using a single keystroke (`b`).
* **URD-FR-02 [Vim Keyboard Ergonomics]**: The user shall navigate and mutate tasks without pointer interaction:
  * Table: `j`/`k` vertical row traversal.
  * Kanban: `h`/`j`/`k`/`l` 2D spatial grid traversal.
  * Status Mutation: `Space` circular status cycling (`TODO` $\to$ `IN_PROGRESS` $\to$ `BLOCKED` $\to$ `DONE` $\to$ `TODO`).
  * Lateral Shift: `Shift+H` / `Shift+L` lateral column shifting with synchronous focus retention.
  * Actions: `1-4` priority assignment, `Enter` inline title rename, `d` deletion, `c` task creation, `/` search focus.
* **URD-FR-03 [Global Escape Dismissal]**: Pressing `Escape` at any time shall instantly dismiss open modals, close dropdown menus, cancel inline editing, and blur active inputs via capture-phase interception.
* **URD-FR-04 [Local-First Persistence]**: The system shall persist all task mutations locally in client-side IndexedDB instantly before background API sync.
* **URD-FR-05 [Solid Surface Contrast]**: The interface shall maintain strict, solid, non-transparent surfaces (`bg-slate-100`/`bg-slate-200` light, `bg-slate-950` dark) with 0ms transition-frozen theme snapping.

### 3.2 Should Have (AI & Graph Intelligence)
* **URD-FR-06 [Topological DAG Critical Path]**: The system shall evaluate task dependency chains using Kahn's topological sort and highlight bottleneck tasks on the Critical Path with visual flame badges.
* **URD-FR-07 [Weekly Progress Summary]**: The system shall aggregate sprint task states into structured overview, blocker, and priority report cards.
* **URD-FR-08 [Meeting Minutes Generator]**: The system shall parse conversational meeting transcripts into structured action items, assignees, and key decisions.
* **URD-FR-09 [Workload & Smart Assignment]**: The system shall evaluate team member skill tags and active WIP complexity to recommend optimal assignees.
* **URD-FR-10 [Git Diff Ticket Synchronizer]**: The system shall parse Unified Git Diffs, extract ticket references (`TSK-X`), and resolve completed tasks automatically.

### 3.3 Could Have (Data Portability & Touch)
* **URD-FR-11 [JSON State Backup]**: The user shall export and import the complete task database as formatted JSON.
* **URD-FR-12 [Mobile Touch Ergonomics]**: The user shall interact via touch gestures (swipe right for DONE, swipe left for BLOCKED) and a docked bottom navigation bar on mobile viewports.

---

## 4. User Operational Scenarios

### Scenario A: High-Velocity Triage (System Architect)
1. Architect opens Koshi (`https://koshi.tupm.qzz.io`) in a browser window.
2. Presses `b` to switch to Kanban view.
3. Uses `h`/`j`/`k`/`l` to navigate to a blocked card (`TSK-105`).
4. Presses `Shift+L` to unblock and advance the task to `DONE`. The focus ring follows the card to the `DONE` column.
5. Presses `v` to inspect the DAG graph and verify that downstream tasks are now unblocked.
6. Presses `Escape` to close the visualizer.

### Scenario B: Sprint Planning & Synthesis (Project Manager)
1. PM clicks `AI Tools ▾` $\to$ `Weekly Summary`.
2. System evaluates current sprint tasks and generates a structured status report with identified blockers and priorities.
3. PM clicks `Copy Report` to export formatted text to the team channel.
4. PM clicks `AI Tools ▾` $\to$ `Meeting Minutes`, pastes unstructured notes from the standup, and generates discrete action items with assigned owners and deadlines.

---

## 5. Contributors & Authorship
* **Lead Architect & Developer**: Phạm Minh Tú (`tupm`)
* **Contributors**:
  * Phạm Văn Huynh
  * Đàm Đức Đôn
