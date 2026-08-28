# KOSHI PROGRESS & GOVERNANCE ENGINE ARCHITECTURE REPORT

**Target Workspace:** `~/koshi`  
**Host Target:** `kirara` (Dev/Build) & `umi` (Live Production: `https://koshi.felixsu.qzz.io`)  
**Assessment Date:** 2026-08-28  
**Status:** **PASSED & VERIFIED IN PRODUCTION**  

---

## 1. RESTRUCTURE EVALUATION & BRANCH INTEGRATION (`restructure/source-docs-split`)

### 1.1. Structural Isolation & Directory Hierarchy
The repository adheres to strict clean architectural isolation:
- **`docs/`**: Retains all engineering specifications, Requirements Documents (URD, SRS), Architecture maps, and Academic Reports (`BAO_CAO_KT1.md`, `architecture.md`, `codebase-map.md`, `user_story.md`).
- **`source_code/backend/`**: Contains the FastAPI REST Engine, SQLAlchemy 2.0 ORM models, SQLite WAL database, Pydantic schemas, and Pytest verification suites.
- **`source_code/frontend/`**: Contains Vue 3.5 Single Page Application (TypeScript / Pinia / Tailwind v4), responsive spatial Kanban, DAG Topo-Sorter, and offline-first IndexedDB synchronization.
- **`source_code/scripts/`**: Automation scripts for packaging submissions (`package_submission.sh`), Word document generation (`generate_docx.py`), and hot SQLite database backups (`backup_db.sh`).

---

## 2. DELAYED PROGRESS ENGINE (CHẬM TIẾN ĐỘ & SLA ENGINE)

### 2.1. Dynamic SLA Overdue & Slip Calculation
Task SLA status is computed dynamically across REST endpoints:
$$\text{is\_overdue} = (\text{due\_date} < \text{now}) \land (\text{status} \ne \text{DONE})$$
$$\text{slip\_days} = \max\left(0, \left\lfloor \frac{\text{now} - \text{due\_date}}{86400} \right\rfloor\right)$$

### 2.2. Schema & Model Implementation
- **Backend Schema (`source_code/backend/app/schemas/task.py`)**: `TaskOut` includes `is_overdue: bool` and `slip_days: int`.
- **Router Computation (`source_code/backend/app/routers/tasks.py`)**: `compute_task_out()` dynamically calculates `is_overdue` and `slip_days` for every task query, card mutation, and status cycle.
- **Frontend Reactive Store (`source_code/frontend/src/stores/taskStore.ts`)**: `syncWithBackend()` maps `is_overdue` and `slip_days` into Pinia state.

---

## 3. ROLE-BASED PRIORITY GOVERNANCE WORKFLOW (RBAC)

### 3.1. Governance State Machine
```
+-------------------------------------------------------------------------------+
| PRIORITY GOVERNANCE STATE TRANSITIONS                                         |
+-------------------------------------------------------------------------------+
| 1. Direct Mutation:                                                           |
|    - PM / OWNER  --> PATCH /tasks/{id} {"priority": "CRITICAL"} --> 200 OK   |
|    - MEMBER      --> PATCH /tasks/{id} {"priority": "CRITICAL"} --> 403 FORBID|
|                                                                               |
| 2. Member Proposal:                                                           |
|    - MEMBER      --> POST /tasks/{id}/request-priority                        |
|                      {"requested_priority": "CRITICAL", "reason": "Spike"}    |
|                      --> Records requested_priority & reason (200 OK)         |
|                                                                               |
| 3. Governance Resolution:                                                     |
|    - PM / OWNER  --> POST /tasks/{id}/approve-priority                        |
|                      --> task.priority = requested_priority, clears request   |
|    - PM / OWNER  --> POST /tasks/{id}/reject-priority                         |
|                      --> clears requested_priority, priority unchanged        |
|    - MEMBER      --> POST /tasks/{id}/approve-priority --> 403 FORBIDDEN      |
+-------------------------------------------------------------------------------+
```

### 3.2. Database & Entity Persistence
- Added fields in `tasks` table and `Task` model:
  - `requested_priority VARCHAR(20)`
  - `priority_request_reason VARCHAR(255)`
  - `priority_requested_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL`
- Maintained relational junction table `task_dependencies` with cascading foreign keys.

---

## 4. VERIFICATION SUITE EXECUTION & RESULTS

### 4.1. Database Initializer & Seeder
```bash
$ python3 source_code/backend/init_db.py
Database initialized with WAL mode and seeded at: /home/felixsu/koshi/source_code/backend/app/data/koshi.db
[Exit Code: 0]
```

### 4.2. Pytest Automated Test Suite
```bash
$ pytest source_code/backend/tests
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/felixsu/koshi/source_code/backend
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.4.0
collected 9 items

source_code/backend/tests/test_ai_and_stats.py ..                        [ 22%]
source_code/backend/tests/test_auth.py ....                              [ 66%]
source_code/backend/tests/test_tasks.py ...                              [100%]

======================= 9 passed, 101 warnings in 5.82s ========================
[Exit Code: 0]
```

### 4.3. Frontend TypeScript & Production Vite Build
```bash
$ npm --prefix source_code/frontend run build
> koshi@1.0.0 build
> vue-tsc -b && vite build

vite v6.4.3 building for production...
✓ 1614 modules transformed.
dist/index.html                   1.66 kB │ gzip:  0.79 kB
dist/assets/index-DExBiVu_.css   62.13 kB │ gzip:  9.95 kB
dist/assets/index-EdcYAKhm.js   227.53 kB │ gzip: 63.12 kB
✓ built in 3.86s
[Exit Code: 0]
```

### 4.4. Automated SQLite Online Hot Backup
```bash
$ bash source_code/scripts/backup_db.sh
[✓] Online hot backup created successfully at: /home/felixsu/koshi/data/backups/koshi_20260828_103306.db
[Exit Code: 0]
```

### 4.5. Live Production Runtime Probes (`umi`)
- **Health Check Probe:**
  ```bash
  $ curl -s https://koshi.felixsu.qzz.io/api/v1/health
  {"status":"healthy","service":"Koshi Project Management Engine","version":"1.0.0"}
  ```
- **Static Assets Check:**
  ```bash
  $ curl -s -I https://koshi.felixsu.qzz.io/vite.svg | head -n 3
  HTTP/2 200 
  content-type: image/svg+xml
  content-length: 1498
  ```
- **Simulated Google OAuth Login:**
  ```bash
  $ curl -s -X POST https://koshi.felixsu.qzz.io/api/v1/auth/google -H "Content-Type: application/json" -d '{"credential": "mock_google_token_pm@tupm.qzz.io"}'
  {"access_token":"...","token_type":"bearer","user":{"id":4,"email":"pm@tupm.qzz.io","full_name":"Phạm Minh Tú (PM)","role":"PM"}}
  ```

---

## 5. SUMMARY DELIVERABLE MATRIX

| Deliverable | Implementation Target | Status | Verification Gate |
|---|---|---|---|
| **Branch Integration** | `docs/` & `source_code/` separation | COMPLETED | Clean monorepo separation |
| **Delayed Task SLA** | `is_overdue`, `slip_days` computation | COMPLETED | `test_overdue_task_sla_calculation` |
| **Priority Governance**| Proposal & Approval State Machine | COMPLETED | `test_priority_governance_workflow_and_rbac` |
| **Frontend Integration**| `types/task.ts`, `api.ts`, `taskStore.ts` | COMPLETED | `npm run build` (0 TS errors) |
| **Online Hot Backup** | `source_code/scripts/backup_db.sh` | COMPLETED | Hot `.db` snapshot in `data/backups/` |
| **Live Deployment** | Deployed to Docker Compose on `umi` | COMPLETED | Live endpoints verified HTTP 200 |
