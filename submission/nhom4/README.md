# KOSHI (輿)

> **High-Velocity, Local-First Project Management System**  
> *Deterministic State Machines • Vue 3 Composition API & Pinia • 2D Spatial Vim Navigation • Topological DAG Prioritization • Schema-Constrained AI Execution*

[![Live Demo](https://img.shields.io/badge/Live%20Production-koshi.felixsu.qzz.io-emerald?style=flat-square)](https://koshi.felixsu.qzz.io)
[![Runtime](https://img.shields.io/badge/Runtime-Vue%203%20Composition%20API-42b883?style=flat-square)](https://vuejs.org)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLite-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![Memory Footprint](https://img.shields.io/badge/Idle%20RAM-%3C15MB-blue?style=flat-square)](#)
[![Action Latency](https://img.shields.io/badge/Action%20Latency-%3C50ms-cyan?style=flat-square)](#)
[![Documentation](https://img.shields.io/badge/Specs-URD%20%26%20SRS-indigo?style=flat-square)](./URD.md)

---

## 1. Executive Summary & Problem Statement

Modern Project Management tools (Jira, Notion, ClickUp, Linear) have succumbed to feature bloat, memory leakages, administrative state-machine overhead, and superficial LLM wrappers. 

```
┌───────────────────────────────┐     ┌───────────────────────────────┐
│     Contemporary PM Tools     │     │             KOSHI             │
├───────────────────────────────┤     ├───────────────────────────────┤
│ 800MB–2GB+ RAM per Electron   │     │ <15MB RAM Idle Web / Mobile   │
│ 1.5s+ modal latency & Diffing │     │ <16ms Optimistic Mutations    │
│ 15–30 mandatory JQL fields    │     │ 4 Strict Deterministic States │
│ Unconstrained hallucinated AI │     │ Schema-Enforced AI Services   │
│ Proprietary CSV lock-in       │     │ Lossless Graph JSON Port      │
└───────────────────────────────┘     └───────────────────────────────┘
```

**KOSHI** eliminates these systemic bottlenecks by operating on five strict architectural principles:
1. **Vue 3 Composition API & Pinia Reactivity**: Fine-grained reactive state and zero visual lag.
2. **Modal-Less 2D Spatial Keyboard Traversal**: High-velocity hotkeys (`b` view toggle, `h`/`j`/`k`/`l` spatial grid navigation, `H`/`L` lateral card shifts, `Space` cyclic status cycling, inline `Enter` edits).
3. **Deterministic State Transitions**: Cyclic invariant: `TODO` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `BLOCKED` $\rightarrow$ `DONE` $\rightarrow$ `TODO`.
4. **Topological DAG Prioritization**: Computes true critical paths mathematically instead of arbitrary story-point poker.
5. **Local-First Persistence & FastAPI Backend**: Zero-latency IndexedDB offline persistence with seamless background FastAPI backend synchronization.

---

## 2. Directory Structure & Architecture

```
koshi/
├── URD.md                   # User Requirements Document (ISO/IEC/IEEE 29148:2018)
├── SRS.md                   # Software Requirements Specification
├── user_story.md            # Agile User Stories & Acceptance Criteria
├── nhom4.docx               # Compiled Formal Academic Word Report
├── README.md                # Project Architecture & Quickstart
├── CLAUDE.md                # Engineering Guidelines & Constraints
├── docker-compose.yml       # Production Multi-Container Orchestration
├── docs/                    # Architectural Specifications & Reports
└── source_code/             # Monorepo Source Code
    ├── frontend/            # Vue 3 + TypeScript + Tailwind CSS Frontend
    ├── backend/             # FastAPI + SQLAlchemy 2.0 + SQLite Backend
    └── scripts/             # Word Generator & Packaging Scripts
```

```mermaid
graph TB
    subgraph UI Layer [Vue 3 + Tailwind CSS]
        App[App.vue Main Shell]
        Table[TaskTable.vue High-Density Grid]
        Kanban[KanbanBoard.vue 2D Spatial Board]
        Modals[AI / DAG / Diff / Create / Auth Modals]
    end

    subgraph State & Logic Engine
        Store[taskStore.ts Pinia Store]
        Kbd[keyboard.ts Vim Dispatcher]
        DAG[dagSorter.ts Topological Graph Evaluator]
        API[api.ts Axios Backend Client]
    end

    subgraph Backend & Storage Layer
        FastAPI[FastAPI Python Backend]
        AI[AI Cascading Service]
        SQLite[(SQLite Database)]
        IDB[(Client IndexedDB)]
    end

    App --> Store
    Table --> Store
    Kanban --> Store
    Modals --> Store

    Store --> DAG
    Store --> Kbd
    Store --> API
    API --> FastAPI
    FastAPI --> AI
    FastAPI --> SQLite
    Store <--> IDB
```

* **Frontend**: Vue 3 + Pinia + TypeScript + Vite + Tailwind CSS (`source_code/frontend/`).
* **Backend**: FastAPI (Python 3.11+) + SQLAlchemy 2.0 + OpenAI / Ollama fallback (`source_code/backend/`).
* **Storage**: IndexedDB (`idb-keyval`) locally, SQLite on server.
* **Deployment**: Docker Compose (`koshi` + `koshi-backend`).

---

## 3. High-Leverage Deterministic AI Integration

KOSHI replaces conversational chat wrappers with structured AI services:

### 3.1. Task Decomposer
Transforms unstructured engineering goals into structured, dependency-linked subtask graphs with complexity ratings.

### 3.2. Weekly Progress Summary
Generates structured executive summaries categorizing completed milestones, active bottlenecks, and immediate sprint priorities.

### 3.3. Meeting Minutes Generator
Parses conversational meeting transcripts to extract attendees, recorded decisions, key discussions, and auto-generated actionable tasks.

### 3.4. Team Workload & Smart Assignment
Evaluates developer skill matches, current active WIP count, and complexity points to balance team velocity.

### 3.5. Git Diff State Synchronizer
Parses Unified Git Diffs and commit messages to automatically transition task states.

### 3.6. Topological DAG Critical Path Evaluator
Constructs an adjacency graph of task dependencies, checks for circular dependencies via Kahn's algorithm, and computes the longest complexity-weighted path ($S=1, M=2, L=3, XL=5$), flagging bottlenecks with the `Flame` indicator.

---

## 4. Keyboard Protocol & Touch Ergonomics

### 4.1. Desktop Keyboard Shortcuts
| Key | Action | Scope |
| :--- | :--- | :--- |
| `b` | Toggle Table / Kanban View | Global |
| `h` / `l` / `←` / `→` | Move left / right between columns | Kanban view |
| `j` / `k` / `↓` / `↑` | Move down / up across tasks / rows | Global |
| `H` / `L` | Shift selected task to adjacent status column | Kanban view |
| `Space` | Cycle task status (`TODO` $\rightarrow$ `IN_PROG` $\rightarrow$ `BLOCKED` $\rightarrow$ `DONE` $\rightarrow$ `TODO`) | Active task |
| `Enter` | Inline title edit mode | Active task |
| `d` / `Backspace` | Delete selected task | Active task |
| `c` | Open task creation modal | Global |
| `1` - `4` | Set priority (`1`: LOW, `2`: MED, `3`: HIGH, `4`: CRITICAL) | Active task |
| `/` | Focus search filter | Global |
| `a` | Open Task Decomposer modal | Global |
| `g` | Open Git Diff analyzer modal | Global |
| `v` | Open Topological DAG visualizer | Global |
| `t` | Toggle Light / Dark mode (0ms snap) | Global |
| `?` | Open keyboard shortcuts help modal | Global |
| `Esc` | Cancel edit / dismiss modal / unfocus search | Global (Capture-phase) |

---

## 5. Specification Documents

Detailed user requirements, IEEE 29148 functional specifications, and user stories:
- [URD.md](./URD.md) — User Requirements Document
- [SRS.md](./SRS.md) — System Requirements Specification
- [user_story.md](./user_story.md) — Agile User Stories & Acceptance Criteria
- [nhom4.docx](./nhom4.docx) — Formal Academic Word Report

---

## 6. Development & Deployment

### 6.1. Local Development
```bash
# Frontend
cd source_code/frontend
npm install
npm run dev

# Backend
cd source_code/backend
python3 init_db.py
uvicorn app.main:app --reload --port 8000
```

### 6.2. Production Build
```bash
cd source_code/frontend
npm run build
```

---

## 7. License & Contributors

* **Team**: Nhóm 04 (ICTU)
* **Lead Architect & Developer**: Phạm Minh Tú (`tupm`)
* **Fullstack Contributor & Testing**: Phạm Văn Huynh
* **Frontend Contributor & Documentation**: Đàm Đức Đôn

Released under the **MIT License**.
