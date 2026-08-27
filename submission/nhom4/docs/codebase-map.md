# Codebase Map - Koshi Project Management Engine

## Repository Directory Hierarchy

```
koshi/
├── backend/
│   ├── app/
│   │   ├── config.py              # Environment configuration & pydantic settings
│   │   ├── database.py            # SQLAlchemy 2.0 database engine & session generator
│   │   ├── main.py                # FastAPI app entrypoint, CORS, lifespan & seed data
│   │   ├── security.py            # JWT token generation, OAuth hash & RBAC dependencies
│   │   ├── models/
│   │   │   └── entities.py        # SQLAlchemy ORM models: User, Project, Sprint, Task, Comment
│   │   ├── routers/
│   │   │   ├── ai.py              # AI PM endpoints: weekly summary, meeting minutes, task decomp
│   │   │   ├── auth.py            # Auth endpoints: register, login, google oauth, me
│   │   │   ├── projects.py        # Project CRUD & ownership management
│   │   │   ├── sprints.py         # Sprint cycles & active sprint tracking
│   │   │   ├── stats.py           # Workload calculation & delayed tasks analysis
│   │   │   ├── tasks.py           # Task CRUD, DAG dependency linking, status cycling
│   │   │   └── users.py           # User management, role elevation & WIP monitoring
│   │   └── schemas/
│   │       ├── ai.py              # Pydantic request/response schemas for AI workflows
│   │       ├── auth.py            # Auth DTOs (GoogleAuthRequest, UserUpdate, Token)
│   │       ├── project.py         # Project & Sprint DTOs
│   │       └── task.py            # Task CRUD schemas & dependency payloads
│   ├── db/
│   │   └── schema.sql             # Pure SQLite 3 DDL schema
│   ├── tests/
│   │   ├── conftest.py            # Test database fixture & TestClient setup
│   │   ├── test_ai.py             # Integration tests for AI PM workflows
│   │   ├── test_auth.py           # Auth, Google OAuth & User management test suite
│   │   ├── test_dag.py            # Topological sort & DAG cycle detection tests
│   │   └── test_tasks.py          # Task lifecycle & status cycling tests
│   ├── init_db.py                 # Standalone script to initialize SQLite database
│   ├── requirements.txt           # Python dependency specifications
│   └── Dockerfile.backend         # Production container definition for FastAPI
├── docs/
│   ├── architecture.md            # Topology, state invariants & algorithm specifications
│   ├── BAO_CAO_KT1.md             # Vietnamese Chapter 1 Report for KT1 Rubric
│   ├── codebase-map.md            # Directory structure & API router inventory (This file)
│   ├── SRS.md                     # ISO/IEC/IEEE 29148:2018 System Requirements Specification
│   ├── URD.md                     # ISO/IEC/IEEE 29148:2018 User Requirements Document
│   └── user-stories.md            # Agile User Stories & Given-When-Then Acceptance Criteria
├── scripts/
│   ├── generate_docx.py           # Python Markdown to DOCX compiler for `nhom1.docx`
│   └── package_submission.sh      # Bash script to package KT1 submission deliverables
├── src/
│   ├── App.vue                    # Root component: docked topbar, statusline, modal mounting
│   ├── app.css                    # Tailwind CSS v4 setup & 0ms animation kill rules
│   ├── main.ts                    # Vue 3 bootstrap with Pinia
│   ├── components/
│   │   ├── AIDecomposerModal.vue  # Goal decomposition modal
│   │   ├── AuthModal.vue          # Google OAuth & Email/Password dialog
│   │   ├── CreateTaskModal.vue    # Quick task creation modal (Hotkey: n)
│   │   ├── DAGVisualizerModal.vue # Interactive Kahn DAG & Critical Path visualizer
│   │   ├── GitDiffModal.vue       # Git diff patch analyzer & task resolver
│   │   ├── KanbanBoard.vue        # 4-column spatial Kanban board with circular wrap
│   │   ├── MeetingMinutesModal.vue# Unstructured meeting note action item extractor
│   │   ├── MobileBottomNav.vue    # Docked mobile navigation bar
│   │   ├── ShortcutsHelpModal.vue # Keyboard shortcut cheatsheet (Hotkey: ?)
│   │   ├── TaskContextMenu.vue   # Right-click contextual menu
│   │   ├── TaskDetailModal.vue    # Full-field interactive Linear-style inspector (Hotkey: Enter)
│   │   ├── TaskTable.vue          # High-density spreadsheet task table view
│   │   ├── WeeklySummaryModal.vue # Executive bulleted sprint summary modal
│   │   └── WorkloadAssignModal.vue# Skill-matched task recommender modal
│   ├── lib/
│   │   ├── aiDecomposer.ts        # Client-side 3-tier heuristic AI cascade
│   │   ├── dag.ts                 # Kahn's Algorithm & Critical Path Method (CPM) solver
│   │   └── keyboard.ts            # Global hotkey capture state machine
│   ├── services/
│   │   └── api.ts                 # Typed HTTP client communicating with FastAPI
│   ├── stores/
│   │   ├── taskStore.ts           # Central Pinia store: local storage sync & state invariants
│   │   └── themeStore.ts          # Dark/light mode theme manager
│   └── types/
│       └── task.ts                # TypeScript interfaces: Task, TaskStatus, TaskPriority, Complexity
├── package.json                   # Frontend npm dependencies and build scripts
├── tsconfig.json                  # TypeScript compiler options (strict mode)
├── vite.config.ts                 # Vite 6 configuration & API reverse proxy
├── Dockerfile.frontend            # Production multi-stage Nginx container
└── docker-compose.yml             # Full-stack container orchestration
```

---

## API Router Inventory

| HTTP Method | Endpoint | Router | Description | RBAC |
|:---|:---|:---|:---|:---|
| `POST` | `/api/v1/auth/register` | `auth.py` | Register user account | Public |
| `POST` | `/api/v1/auth/login` | `auth.py` | Authenticate via email/password | Public |
| `POST` | `/api/v1/auth/google` | `auth.py` | Exchange Google ID Token for JWT | Public |
| `GET` | `/api/v1/auth/me` | `auth.py` | Fetch authenticated profile | Authenticated |
| `GET` | `/api/v1/users` | `users.py` | List team members with WIP metrics | Authenticated |
| `PATCH` | `/api/v1/users/{id}` | `users.py` | Update member role & skills | PM Only |
| `GET` | `/api/v1/projects` | `projects.py` | List projects for user | Authenticated |
| `GET` | `/api/v1/tasks?project_id={id}` | `tasks.py` | Query project tasks | Authenticated |
| `POST` | `/api/v1/tasks` | `tasks.py` | Create new task | Authenticated |
| `PATCH` | `/api/v1/tasks/{id}` | `tasks.py` | Update task fields | Authenticated |
| `DELETE` | `/api/v1/tasks/{id}` | `tasks.py` | Remove task and cascade dependencies | Authenticated |
| `POST` | `/api/v1/tasks/{id}/cycle-status` | `tasks.py` | Cyclic status advancement | Authenticated |
| `POST` | `/api/v1/ai/decompose` | `ai.py` | Decompose high-level goal to subtasks | Authenticated |
| `POST` | `/api/v1/ai/weekly-summary` | `ai.py` | Generate executive sprint report | Authenticated |
| `POST` | `/api/v1/ai/meeting-minutes` | `ai.py` | Extract action items from notes | Authenticated |
| `POST` | `/api/v1/ai/recommend-assignment` | `ai.py` | Match task with team skills | Authenticated |
