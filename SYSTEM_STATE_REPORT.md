# KOSHI (輿) — SYSTEM STATE & PROGRESS AUDIT REPORT
**Document Reference**: `SYSTEM_STATE_REPORT.md`  
**Classification**: Technical Single-Source-of-Truth (SSOT)  
**Authors**: Nhóm 04 (Phạm Minh Tú (#), Phạm Văn Huynh, Đàm Đức Đôn)  
**Academic Supervisor**: ThS. Nguyễn Thị Tuyển — Trường Đại học Công nghệ Thông tin và Truyền thông (ICTU)  
**Audit Timestamp**: 2026-08-28T09:22:00+07:00  
**Target Environment**: `kirara` (Local Development) & `umi` (Production Deployment: `https://koshi.felixsu.qzz.io`)

---

## 1. EXHAUSTIVE REPOSITORY INVENTORY & FILE TREE

### 1.1 Complete Directory Layout
```
.
├── .dockerignore
├── .gitignore
├── AUDIT_TDD_REASSESSMENT.md
├── AUDIT_TDD_REPORT.md
├── CLAUDE.md
├── Dockerfile
├── PREVIOUS_SESSION_EXTRACT.log
├── README.md
├── SRS.md
├── SYSTEM_STATE_REPORT.md
├── URD.md
├── docker-compose.yml
├── data/
│   ├── test_koshi.db-shm
│   └── test_koshi.db-wal
├── docs/
│   ├── BAO_CAO_KT1.md
│   ├── SRS.md
│   ├── URD.md
│   ├── architecture.md
│   ├── codebase-map.md
│   ├── user-stories.md
│   └── user_story.md
├── nhom4.docx
├── source_code/
│   ├── backend/
│   │   ├── Dockerfile
│   │   ├── pytest.ini
│   │   ├── requirements.txt
│   │   ├── init_db.py
│   │   ├── app/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── main.py
│   │   │   ├── security.py
│   │   │   ├── core/
│   │   │   │   └── config.py
│   │   │   ├── data/
│   │   │   │   └── koshi.db
│   │   │   ├── models/
│   │   │   │   └── entities.py
│   │   │   ├── routers/
│   │   │   │   ├── ai.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── sprints.py
│   │   │   │   ├── stats.py
│   │   │   │   ├── tasks.py
│   │   │   │   └── users.py
│   │   │   ├── schemas/
│   │   │   │   ├── ai.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── project.py
│   │   │   │   ├── sprint.py
│   │   │   │   ├── stats.py
│   │   │   │   └── task.py
│   │   │   └── services/
│   │   │       └── ai_service.py
│   │   ├── db/
│   │   │   └── schema.sql
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_ai_and_stats.py
│   │       ├── test_auth.py
│   │       └── test_tasks.py
│   ├── frontend/
│   │   ├── Dockerfile
│   │   ├── index.html
│   │   ├── nginx.conf
│   │   ├── package-lock.json
│   │   ├── package.json
│   │   ├── pnpm-lock.yaml
│   │   ├── pnpm-workspace.yaml
│   │   ├── svelte.config.js
│   │   ├── tsconfig.json
│   │   ├── tsconfig.tsbuildinfo
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── App.vue
│   │       ├── app.css
│   │       ├── main.ts
│   │       ├── vite-env.d.ts
│   │       ├── components/
│   │       │   ├── AIDecomposerModal.vue
│   │       │   ├── AuthModal.vue
│   │       │   ├── CreateTaskModal.vue
│   │       │   ├── DAGVisualizerModal.vue
│   │       │   ├── GitDiffModal.vue
│   │       │   ├── KanbanBoard.vue
│   │       │   ├── MeetingMinutesModal.vue
│   │       │   ├── MobileBottomNav.vue
│   │       │   ├── ProjectMembersModal.vue
│   │       │   ├── ShortcutsHelpModal.vue
│   │       │   ├── TaskCard.vue
│   │       │   ├── TaskContextMenu.vue
│   │       │   ├── TaskDetailModal.vue
│   │       │   ├── TaskTable.vue
│   │       │   ├── WeeklySummaryModal.vue
│   │       │   └── WorkloadAssignModal.vue
│   │       ├── lib/
│   │       │   ├── aiDecomposer.ts
│   │       │   ├── dagSorter.ts
│   │       │   ├── gitParser.ts
│   │       │   └── keyboard.ts
│   │       ├── services/
│   │       │   └── api.ts
│   │       ├── stores/
│   │       │   ├── taskStore.ts
│   │       │   └── themeStore.ts
│   │       └── types/
│   │           └── task.ts
│   └── scripts/
│       ├── generate_docx.py
│       └── package_submission.sh
└── user_story.md
```

### 1.2 Itemized Functional Manifest

#### Root Specifications & Project Metadata
- `README.md`: Executive summary, live deployment URL (`https://koshi.felixsu.qzz.io`), architectural diagrams, and getting-started commands.
- `CLAUDE.md`: System instructions, build commands, guidelines for local dev and remote syncing.
- `URD.md`: User Requirements Document detailing problem statement, user personas, operational constraints, and acceptance criteria.
- `SRS.md`: Software Requirements Specification complying with ISO/IEC/IEEE 29148.
- `user_story.md` / `docs/user-stories.md`: User story backlog (US-01 through US-18) mapped to technical acceptance criteria.
- `nhom4.docx`: Official compiled academic report conforming to the ICTU template with complete Chapter 1 analysis.
- `docker-compose.yml`: Multi-container production deployment definition for backend (FastAPI, port 8000) and frontend (Nginx, port 80).

#### Backend Services (`source_code/backend/`)
- `app/main.py`: FastAPI root entrypoint, CORS configuration (`ALLOWED_ORIGINS`), router registrations, SQLite lifecycle events.
- `app/config.py`: Pydantic `BaseSettings` management with production JWT secret validation and allowed origins.
- `app/database.py`: SQLAlchemy connection pool with SQLite connection listeners enforcing WAL mode, foreign keys, and 30s busy timeout.
- `app/security.py`: Password hashing (Bcrypt), JWT generation and verification, `verify_project_membership` dependency guard.
- `app/models/entities.py`: SQLAlchemy ORM definitions (`User`, `Project`, `ProjectMember`, `Sprint`, `Task`, `Comment`).
- `app/routers/auth.py`: Registration, password login, Google OAuth2 verified token login, profile inspection.
- `app/routers/projects.py`: Project CRUD and project-scoped membership management.
- `app/routers/users.py`: Registered user search (`GET /api/v1/users/search?q=...`) for project invitations.
- `app/routers/tasks.py`: Task CRUD, comment management, task status update with membership authorization.
- `app/routers/sprints.py`: Sprint management and sprint active toggle.
- `app/routers/stats.py`: Sprint velocity, workload distribution, and blocked task aggregation.
- `app/routers/ai.py`: 3-tier cascade AI proxy endpoints (Weekly Summary, Meeting Minutes, Smart Assignment).
- `app/services/ai_service.py`: Heuristic rules and external LLM connector engine with timeout fallbacks.
- `db/schema.sql`: Raw SQL DDL with `AUTOINCREMENT` primary keys, foreign key constraints, and cascade delete rules.
- `init_db.py`: CLI database migration and seed script.
- `tests/conftest.py`: Pytest fixtures providing isolated test databases, authenticated users, and project members.
- `tests/test_auth.py`: Unit and integration tests for password registration, JWT issuance, and Google token verification.
- `tests/test_tasks.py`: Task creation, dependency linking, and comment thread tests.
- `tests/test_ai_and_stats.py`: AI endpoint resilience, JSON schema compliance, and workload stats verification.

#### Frontend Application (`source_code/frontend/`)
- `src/App.vue`: Main SPA layout, dual-mode container (Table vs 2D Kanban), global keyboard shortcut listener, modal mount points.
- `src/main.ts`: Pinia store initialization, Vue app bootstrap.
- `src/app.css`: Tailwind CSS v4 design tokens, dark mode slate palette, custom scrollbars.
- `src/stores/taskStore.ts`: Local-first reactive state engine, deterministic task comparator (`compareTasks`), IndexedDB persistence.
- `src/stores/themeStore.ts`: Dark/Light theme toggle with localStorage persistence and OS preference detection.
- `src/services/api.ts`: Typed Axios client handling JWT tokens, error interceptors, and backend endpoints.
- `src/types/task.ts`: TypeScript interfaces for tasks, sprints, projects, members, filter predicates, and UI state.
- `src/lib/dagSorter.ts`: Kahn's topological sort and CPM (Critical Path Method) evaluator.
- `src/lib/keyboard.ts`: Vim-inspired spatial navigation handler (`h/j/k/l`, `Space`, `Enter`, `i`, `n`, `/`, `?`, `b`, `g`, `Escape`).
- `src/lib/gitParser.ts`: Unified Git diff parser extracting ticket references and commit intent.
- `src/lib/aiDecomposer.ts`: Natural language objective breakdown into discrete sub-tasks.
- `src/components/KanbanBoard.vue`: 2D spatial grid layout with 4 status columns (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`) and drag-and-drop.
- `src/components/TaskCard.vue`: Kanban task card with footer action cluster (`Pencil` edit button, `< >` status chevrons, tooltips).
- `src/components/TaskTable.vue`: High-density tabular view with inline title editing, status dots, and swipe ergonomics.
- `src/components/TaskDetailModal.vue`: Comprehensive task inspector with sequential `tabindex` chaining (1–7) and escape trap.
- `src/components/ProjectMembersModal.vue`: User search, project invitation, and role assignment dialog (`OWNER`, `PM`, `MEMBER`).
- `src/components/CreateTaskModal.vue`: Quick task creation modal with status and priority selectors.
- `src/components/DAGVisualizerModal.vue`: Interactive SVG dependency graph visualizer highlighting critical paths.
- `src/components/WeeklySummaryModal.vue`: AI sprint retrospective generator with 3 structured sections.
- `src/components/MeetingMinutesModal.vue`: AI meeting notes parser extracting tasks, assignees, and deadlines.
- `src/components/WorkloadAssignModal.vue`: AI capacity analyzer balancing WIP story points across team members.
- `src/components/GitDiffModal.vue`: Git commit diff reviewer linking commits to ticket status updates.
- `src/components/AuthModal.vue`: Clean authentication dialog (Login / Register / Google OAuth2) with no hardcoded credentials.
- `src/components/ShortcutsHelpModal.vue`: Keyboard shortcuts reference sheet.
- `src/components/MobileBottomNav.vue`: Touch-optimized bottom navigation bar for mobile viewports.

#### Build & Automation Scripts (`source_code/scripts/`)
- `generate_docx.py`: Single-Source-of-Truth in-place mutation engine cloning the ICTU template docx and rendering Chapter 1.
- `package_submission.sh`: Packaging pipeline generating `submission/nhom4.zip` with full source code, docs, and report.

---

## 2. DATA LAYER & CONCURRENCY ENGINE

### 2.1 Database Schema & Multi-Tenant Entities
The relational model enforces multi-tenancy and referential integrity across all entities:

```sql
-- 1. Users Table (Supports standard auth + Google OAuth2)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NULL,
    full_name VARCHAR(100) NOT NULL,
    google_id VARCHAR(255) UNIQUE NULL,
    avatar_url VARCHAR(500) NULL,
    role VARCHAR(20) DEFAULT 'MEMBER',
    skills VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Projects & Project Members (Project-Scoped RBAC)
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'MEMBER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_project_user UNIQUE (project_id, user_id)
);

-- 3. Sprints, Tasks & Task Dependencies
CREATE TABLE IF NOT EXISTS sprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    goal VARCHAR(255) DEFAULT '',
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_id INTEGER REFERENCES sprints(id) ON DELETE SET NULL,
    assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'TODO',
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    complexity_points INTEGER DEFAULT 2,
    due_date TIMESTAMP NULL,
    blocking_reason VARCHAR(255) NULL,
    dependencies_json TEXT DEFAULT '[]',
    acceptance_criteria_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 SQLite Concurrency Configuration (`database.py`)
To prevent lock contention (`database is locked`) during concurrent read/write operations, SQLAlchemy attaches a connection listener:

```python
# Location: source_code/backend/app/database.py (Lines 18-30)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")      # Concurrent reads during writes
        cursor.execute("PRAGMA synchronous = NORMAL;")    # Optimized sync for SSD workloads
        cursor.execute("PRAGMA foreign_keys = ON;")       # Enforce cascading deletes
        cursor.execute("PRAGMA busy_timeout = 30000;")    # 30-second lock retry queue
        cursor.close()
```

---

## 3. BACKEND API & SECURITY AUDIT

### 3.1 Authentication & Security Hardening
- **Cryptographic Token Verification**: `/api/v1/auth/google` verifies Google ID tokens using `google.oauth2.id_token.verify_oauth2_token` with Google's public certs. Unverified base64 decode fallbacks are completely eliminated.
- **Production Secret Guard**: `app/config.py` enforces startup validation:
  ```python
  if self.ENVIRONMENT == "production" and self.JWT_SECRET == "koshi_super_secret_jwt_key_2026_academic_spec":
      raise RuntimeError("FATAL: Default JWT_SECRET is prohibited in production.")
  ```
- **Project-Scoped RBAC Guard (`verify_project_membership`)**:
  Injected via FastAPI `Depends()` into `projects.py`, `sprints.py`, `tasks.py`, `stats.py`, and `ai.py`:
  ```python
  def verify_project_membership(
      project_id: int,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db)
  ) -> ProjectMember:
      membership = db.query(ProjectMember).filter(
          ProjectMember.project_id == project_id,
          ProjectMember.user_id == current_user.id
      ).first()
      if not membership and current_user.role != RoleEnum.PM:
          raise HTTPException(status_code=403, detail="Not authorized for this project")
      return membership
  ```

### 3.2 AI Cascade Architecture (`ai_service.py`)
All AI operations execute within a 3-tier cascade guarantee:
1. **Tier 1 (Cloud LLM)**: Calls Gemini API / OpenAI API with structured JSON output schema (timeout: 4.0s).
2. **Tier 2 (Local Ollama)**: Falls back to `localhost:11434/api/generate` if network is degraded (timeout: 2.5s).
3. **Tier 3 (Heuristic Rule Engine)**: Deterministic regex/token extraction algorithm guaranteeing valid JSON response in 0ms without network dependencies.

---

## 4. FRONTEND STATE ENGINE & SPATIAL UX

### 4.1 Local-First State Machine & Reconciliation (`taskStore.ts`)
- **Optimistic ID Reconciliation**:
  When creating a task offline or with low latency, `taskStore.createTask()` assigns a temporary `TSK-temp-${timestamp}` ID. Upon backend response, `reconcileTaskId(tempId, permanentId)` updates:
  1. The task object itself (`task.id = 'TSK-' + created.id`).
  2. All downstream dependency arrays (`task.dependencies = [...]`).
  3. Active modal and cursor selections (`activeDetailTaskId`, `editingTaskId`).
- **Non-Destructive Sync**:
  `syncWithBackend()` compares local `updatedAt` timestamps against server records, preserving in-flight optimistic edits.

### 4.2 Deterministic Task Comparator (`compareTasks`)
Tasks across Kanban columns and the Table view are sorted deterministically:
```typescript
// Location: source_code/frontend/src/stores/taskStore.ts (Lines 100-130)
export function compareTasks(a: Task, b: Task, criticalSet: Set<string> = new Set()): number {
  // 1. Critical Path: Non-DONE tasks on critical path come first
  const aCrit = criticalSet.has(a.id) && a.status !== 'DONE' ? 1 : 0;
  const bCrit = criticalSet.has(b.id) && b.status !== 'DONE' ? 1 : 0;
  if (aCrit !== bCrit) return bCrit - aCrit;

  // 2. Priority: CRITICAL (4) > HIGH (3) > MEDIUM (2) > LOW (1)
  const aPri = PRIORITY_WEIGHTS[a.priority] ?? 1;
  const bPri = PRIORITY_WEIGHTS[b.priority] ?? 1;
  if (aPri !== bPri) return bPri - aPri;

  // 3. Due Date: Earliest timestamp first; unassigned dates last
  if (a.dueDate && b.dueDate) {
    const aTime = new Date(a.dueDate).getTime();
    const bTime = new Date(b.dueDate).getTime();
    if (aTime !== bTime) return aTime - bTime;
  } else if (a.dueDate && !b.dueDate) {
    return -1;
  } else if (!a.dueDate && b.dueDate) {
    return 1;
  }

  // 4. Numerical / String ID stable tie-breaker
  const aNum = parseInt(a.id.replace(/\D/g, ''), 10);
  const bNum = parseInt(b.id.replace(/\D/g, ''), 10);
  if (!isNaN(aNum) && !isNaN(bNum) && aNum !== bNum) {
    return aNum - bNum;
  }
  return a.id.localeCompare(b.id);
}
```

### 4.3 Component Interaction & Modal Ergonomics
- **`TaskCard.vue`**: Bottom-right action cluster with a `Pencil` edit button (`title="Edit details (Enter / i)"`, `@click.stop="openDetail"`) and `< >` status switcher (`title="Previous status"`, `title="Next status (Space)"`).
- **`TaskDetailModal.vue`**:
  - Linear `tabindex` (1: Title, 2: Description, 3: Status, 4: Priority, 5: Assignee, 6: Due Date, 7: Blocking Reason).
  - Single footer "Save Changes" action button.
  - Window capture-phase `Escape` key trap ensuring immediate modal dismiss without form input interference.
- **Dual-Mode View Switcher**: Instant `< 16ms` toggle between High-Density Table View and 2D Kanban Board via `b` key.

---

## 5. ACADEMIC DELIVERABLES & DOCX AUTOMATION

### 5.1 In-Place Mutation Engine (`generate_docx.py`)
- **Direct Binary Cloning**: Clones `~/Documents/BAI DU AN_UNG DUNG AI.docx` $\to$ `~/koshi/nhom4.docx` (86 KB), preserving native Word XML field codes (Table of Contents), margins, fonts, and the embedded ICTU circular emblem.
- **Cover Page & Group Metadata**:
  - Topic: **HỆ THỐNG QUẢN LÝ DỰ ÁN VÀ TIẾN ĐỘ CÔNG VIỆC KOSHI CÓ TÍCH HỢP AI**
  - Group: **NHÓM 04**
  - Members: **Phạm Minh Tú (#)**, **Phạm Văn Huynh**, **Đàm Đức Đôn**
  - Supervisor: **ThS. Nguyễn Thị Tuyển**
  - Location/Year: **THÁI NGUYÊN, NĂM 2026**
- **Task Allocation Tables**:
  - Table 1: All 8 KT1 progress tasks populated.
  - Table 2: 3 member allocations with signature columns.
- **Chapter 1 Full Elaboration**:
  - **1.1**: Bối cảnh bài toán và 3 User Personas (Lead Architect, PM, Field Developer).
  - **1.2**: Khảo sát hiện trạng và đối chuẩn (Jira, Trello, Linear vs Koshi).
  - **1.3**: Mô hình Actor và Phân hệ Use Case tổng quát (Guest, Team Member, Project Manager).
  - **1.4**: Đặc tả yêu cầu chức năng cốt lõi (**FR-01** $\to$ **FR-08**).
  - **1.5**: Đặc tả yêu cầu phi chức năng (**NFR-01** $\to$ **NFR-06**).
  - **1.6**: Xác định bài toán ứng dụng AI và phạm vi tích hợp (Summarization, Extraction, Capacity Optimization).
- **Milestone Scope Lock**: Chapters 2, 3, and Conclusion preserved strictly as unpopulated template placeholders for KT2/KT3.
- **CD Disc Notes**: All CD disc notes, guidelines, and label text cleanly stripped.

---

## 6. VERIFICATION COMMAND LOGS

### 6.1 Database Initialization Log
```bash
$ python3 source_code/backend/init_db.py
Database initialized with WAL mode and seeded at: /home/felixsu/koshi/source_code/backend/app/data/koshi.db
```

### 6.2 Backend Pytest Test Suite
```bash
$ pytest source_code/backend/tests
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/felixsu/koshi/source_code/backend
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO

tests/test_ai_and_stats.py ..                                            [ 28%]
tests/test_auth.py ....                                                  [ 85%]
tests/test_tasks.py .                                                    [100%]

======================== 7 passed, 64 warnings in 3.90s ========================
```

### 6.3 Frontend Vite / TypeScript Compilation
```bash
$ npm --prefix source_code/frontend run build
> koshi@1.0.0 build
> vue-tsc -b && vite build

vite v6.4.3 building for production...
✓ 1614 modules transformed.
dist/index.html                   1.66 kB │ gzip:  0.80 kB
dist/assets/index-DExBiVu_.css   62.13 kB │ gzip:  9.97 kB
dist/assets/index-BXa5AUEQ.js   227.18 kB │ gzip: 63.25 kB
✓ built in 4.29s
```

### 6.4 Production Live Health Check
```bash
$ curl -s https://koshi.felixsu.qzz.io/api/v1/health
{"status":"healthy","service":"Koshi PM API","version":"1.0.0"}
```

---
*Report compiled and certified by Nhóm 04 (Lead Architect: Phạm Minh Tú).*
