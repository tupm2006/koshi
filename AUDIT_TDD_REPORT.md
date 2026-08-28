# TECHNICAL DUE DILIGENCE (TDD) AUDIT REPORT

**Target System:** KOSHI Project Management System  
**Audit Scope:** `source_code/backend/`, `source_code/frontend/`, Root Deployment Manifests, Database & Infrastructure Architecture  
**Assessment Date:** 2026-08-28  
**Audit Perspective:** Principal Systems Auditor & Technical Due Diligence Assessor  
**Operational Horizon:** 18 Months  

---

## 1. EXECUTIVE RISK SUMMARY & DEPLOYMENT VERDICT

### 1.1. Go / No-Go Deployment Verdict
**VERDICT: REJECTED (FATAL NO-GO FOR PRODUCTION MULTI-TENANT DEPLOYMENT)**

The codebase exhibits catastrophic vulnerabilities, complete absence of tenant isolation boundaries, zero database concurrency safeguards, broken authentication validation, and destructive client-server state desynchronization. Deploying this system to production in its current state will result in immediate remote account takeover, cross-tenant data leakage, SQLite write-lock deadlocks under minimal concurrency, and silent data destruction.

### 1.2. 18-Month Cost & Effort Projection Overview
* **Remediation Effort to Minimum Production Viability:** **410 Engineering Hours** (approx. 2.5 months full-time senior engineer).
* **18-Month Maintenance & Extension Cost:** **1,280 Engineering Hours** solely to maintain stability, rewrite flawed data synchronization, replace SQLite with PostgreSQL, and remediate systemic technical debt.
* **Compound Fragility Index:** **CRITICAL (9.4 / 10)**. Fragility compounds across zero frontend tests, missing database migrations, unverified authentication fallback, and broken offline-first data reconciliation.

---

## 2. PILLAR 1: DEAL-KILLER TRIAGE & SECURITY POSTURE

```
+---------------------------------------------------------------------------------------+
| DEAL-KILLER RISK REGISTER: SECURITY & AUTHENTICATION                                 |
+------------------------------------+---------------+----------------------------------+
| Risk Item                          | Vulnerability | File / Line Reference            |
+------------------------------------+---------------+----------------------------------+
| Remote Unauthenticated Takeover    | CWE-347       | `app/routers/auth.py:67-81`      |
| Hardcoded Cryptographic Secrets    | CWE-798       | `app/config.py:13`, `compose:10` |
| Total Broken Object Authorization  | CWE-639       | `app/routers/tasks.py:21-120`    |
| Global Cross-Tenant Data Leakage   | CWE-200       | `app/routers/projects.py:32, 58` |
| Insecure Permissive CORS           | CWE-942       | `app/main.py:180-186`            |
+------------------------------------+---------------+----------------------------------+
```

### 2.1. Critical Security Vulnerabilities (Deal-Killers)

#### 2.1.1. Remote Authentication Bypass via Unverified Google JWT (CWE-347 / CWE-287)
* **Location:** [`source_code/backend/app/routers/auth.py:67-81`](file:///home/felixsu/koshi/source_code/backend/app/routers/auth.py#L67-L81)
* **Mechanism:** In `/api/auth/google`, when `id_token.verify_oauth2_token` raises an exception (e.g., in offline/sandbox environments, invalid issuer, or expired token), execution falls into an insecure fallback block:
```python
except Exception:
    # Robust fallback for JWT token decoding in test / sandbox environments
    try:
        parts = req.credential.split(".")
        if len(parts) >= 2:
            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            email = decoded.get("email")
            full_name = decoded.get("name") ...
            google_id = decoded.get("sub")
```
* **Impact:** **Total Authentication Bypass.** Any attacker can craft an arbitrary base64 JSON payload with `{"email": "pm@tupm.qzz.io", "sub": "attacker-id"}` without any cryptographic signature. The server unconditionally accepts this payload, creates an authenticated session, and returns a valid Bearer JWT giving the attacker full administrative access. This bypass is codified in the test suite ([`test_auth.py:45-63`](file:///home/felixsu/koshi/source_code/backend/tests/test_auth.py#L45-L63)).
* **Remediation:** Remove the fallback decoding block entirely. Enforce cryptographic validation against Google's public JWKS endpoints with strict audience, issuer, and signature checks.

#### 2.1.2. Hardcoded Cryptographic Signing Secrets & Seed Passwords (CWE-798)
* **Locations:**
  * [`source_code/backend/app/config.py:13`](file:///home/felixsu/koshi/source_code/backend/app/config.py#L13): `JWT_SECRET: str = "koshi_super_secret_jwt_key_2026_academic_spec"`
  * [`docker-compose.yml:10`](file:///home/felixsu/koshi/docker-compose.yml#L10): `- JWT_SECRET=koshi_super_secret_jwt_key_2026_academic_spec`
  * [`source_code/backend/app/main.py:28, 35`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L28): `hashed_password=get_password_hash("koshi123")`
  * [`source_code/frontend/src/components/AuthModal.vue:15, 42`](file:///home/felixsu/koshi/source_code/frontend/src/components/AuthModal.vue#L15): `const password = ref('koshi123');`
* **Impact:** Any attacker with knowledge of the repository or standard defaults can forge valid HS256 JWT tokens for any `user_id` offline, completely bypassing authentication middleware.
* **Remediation:** Enforce mandatory startup validation that raises an unrecoverable exception if `JWT_SECRET` is unset or equals the default string. Generate secrets via `/dev/urandom` / cryptographic vault.

#### 2.1.3. Complete Absence of Broken Object Level Authorization (BOLA / IDOR) (CWE-639)
* **Locations:**
  * [`source_code/backend/app/routers/tasks.py:21, 31, 56, 62, 84, 92, 107`](file:///home/felixsu/koshi/source_code/backend/app/routers/tasks.py#L21-L120)
  * [`source_code/backend/app/routers/sprints.py:13-30`](file:///home/felixsu/koshi/source_code/backend/app/routers/sprints.py#L13-L30)
  * [`source_code/backend/app/routers/projects.py:32, 58, 69`](file:///home/felixsu/koshi/source_code/backend/app/routers/projects.py#L32-L75)
* **Mechanism:**
  * In `GET /api/tasks?project_id=X`: There is zero validation that `current_user` belongs to `project_id`.
  * In `POST /api/tasks`: Any authenticated user can inject tasks into any project and assign them to any user.
  * In `PATCH /api/tasks/{task_id}`, `DELETE /api/tasks/{task_id}`, `POST /api/tasks/{task_id}/cycle-status`: The endpoints query `Task` strictly by `task_id` without verifying project membership or tenant ownership.
  * In `GET /api/projects`: Executes `db.query(Project).all()`, leaking every project across all tenants to any standard user.
* **Impact:** Complete cross-tenant data compromise and unauthorized state mutation. A standard `MEMBER` in Tenant A can delete, modify, or inspect all tasks and sprints in Tenant B.
* **Remediation:** Implement a centralized database tenancy/membership dependency `get_project_member(project_id, current_user)` that evaluates `ProjectMember` records and enforces RBAC on every router dependency.

#### 2.1.4. Insecure Wildcard CORS with Credentials (CWE-942)
* **Location:** [`source_code/backend/app/main.py:180-186`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L180-L186)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
* **Impact:** Misconfigured origin reflection. While browsers block wildcard origins when `credentials=true` with cookies, exposing this on Bearer token endpoints permits cross-origin script execution and credential theft in environments using reverse proxies or embedded webviews.
* **Remediation:** Restrict `allow_origins` to explicitly configured domain names injected via environment variables.

#### 2.1.5. Token Revocation & Session Lifecycle Deficit
* **Location:** [`source_code/backend/app/config.py:15`](file:///home/felixsu/koshi/source_code/backend/app/config.py#L15), [`source_code/frontend/src/services/api.ts:123`](file:///home/felixsu/koshi/source_code/frontend/src/services/api.ts#L123)
* **Mechanism:** JWT expiration is statically set to 7 days (`60 * 24 * 7`). Logout on the client merely discards the token from `localStorage`. No server-side revocation list, token versioning, or Redis blocklist exists.
* **Impact:** Once a JWT is issued or leaked, it cannot be revoked. Password resets or role demotions do not invalidate active tokens.
* **Remediation:** Shorten access token lifetime to 15 minutes, implement refresh token rotation stored in HTTP-only cookies, and implement server-side revocation tracking.

### 2.2. Single-Person Bus Factor & Operational Fragility
* **Deployment Automation:** Root [`docker-compose.yml`](file:///home/felixsu/koshi/docker-compose.yml#L38-L39) references an external network `proxy-net: external: true`. Running `docker compose up` on a bare-metal server immediately crashes unless the network is manually pre-created.
* **Documentation vs Reality Gap:** Documentation references live domain `koshi.felixsu.qzz.io`, but no provisioning scripts (Terraform/Ansible), SSL renewal hooks, or secret bootstrapping automation exist in the repository. A new engineer cannot deploy the system from bare metal in $<30$ minutes without unrecorded oral instructions.

---

## 3. PILLAR 2: DATA INTEGRITY & DATABASE FAILURE MODES

```
+---------------------------------------------------------------------------------------+
| DATABASE FAILURE MODE ANALYSIS                                                        |
+------------------------------+--------------------+-----------------------------------+
| Failure Mode                 | Current State      | Consequence Under Concurrency     |
+------------------------------+--------------------+-----------------------------------+
| Journal Mode                 | DELETE (Default)   | Exclusive file lock on writes     |
| Busy Timeout                 | Unset (Default 5s) | `OperationalError: db locked`     |
| Foreign Key Enforcement      | OFF (Default)      | Silent orphaned cascade records   |
| Migration Management         | Ad-hoc in main.py  | Split-brain DDL vs SQLAlchemy     |
| Snapshot / Backup Automation | None               | 100% data loss on corruption      |
+------------------------------+--------------------+-----------------------------------+
```

### 3.1. SQLite Write-Lock Contention & Concurrency Bottlenecks
* **Locations:**
  * [`source_code/backend/app/database.py:13-16`](file:///home/felixsu/koshi/source_code/backend/app/database.py#L13-L16)
  * [`docker-compose.yml:9, 16`](file:///home/felixsu/koshi/docker-compose.yml#L9)
* **Vulnerability Analysis:**
  1. **Rollback Journal Mode (`DELETE`):** SQLite defaults to `DELETE` journal mode when WAL is not explicitly invoked. In this mode, any write operation (task creation, status cycle, comment) acquires an exclusive lock on the entire database file (`/app/data/koshi.db`), blocking all concurrent reads and writes across all Uvicorn worker threads.
  2. **Missing `busy_timeout` Configuration:** The SQLAlchemy engine connection parameters only configure `check_same_thread: False`. No `timeout` is passed to SQLite. If two requests attempt to commit simultaneously (e.g., 20 users dragging Kanban cards or cycling statuses), transactions exceed the default timeout and throw unhandled `sqlite3.OperationalError: database is locked`, returning HTTP 500 to clients.
  3. **No Connection Pool Queuing:** With multi-threaded ASGI workers, concurrent asynchronous coroutines contending for the single SQLite connection pool trigger thread-safety collisions and locked-database crashes.
* **Remediation Code Required:**
```python
# Required immediate fix for SQLite stability
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA busy_timeout = 30000;") # 30 seconds
    cursor.close()
```

### 3.2. Foreign Key & Referential Integrity Failure
* **Locations:**
  * [`source_code/backend/db/schema.sql:20, 26, 45, 61`](file:///home/felixsu/koshi/source_code/backend/db/schema.sql#L20)
  * [`source_code/backend/app/database.py:13-16`](file:///home/felixsu/koshi/source_code/backend/app/database.py#L13-L16)
* **Vulnerability Analysis:**
  SQLite disables foreign key enforcement by default on every new database connection. Because `PRAGMA foreign_keys = ON;` is never executed in `database.py`, all `ON DELETE CASCADE` clauses in `schema.sql` and SQLAlchemy relationships are **completely ignored at the database engine level**.
* **Impact:** Deleting a user or project leaves orphaned records in `project_members`, `tasks`, `sprints`, `comments`, and `task_dependencies`. The database rapidly accumulates corrupt dangling references that trigger `500 Internal Server Error` exceptions when joined queries encounter `None` relationships.

### 3.3. Schema Split-Brain & Unmanaged Startup Migrations
* **Locations:**
  * [`source_code/backend/db/schema.sql:44`](file:///home/felixsu/koshi/source_code/backend/db/schema.sql#L44): `id VARCHAR(32) PRIMARY KEY` (Task ID defined as string e.g. `'TSK-1'`)
  * [`source_code/backend/app/models/entities.py:89`](file:///home/felixsu/koshi/source_code/backend/app/models/entities.py#L89): `id = Column(Integer, primary_key=True)` (Task ID defined as auto-increment Integer)
  * [`source_code/backend/app/main.py:140-164`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L140-L164): Custom `migrate_database()` function executing raw `ALTER TABLE` on FastAPI startup.
* **Vulnerability Analysis:**
  * The database schema is bifurcated. If initialized via `init_db.py` (which reads `schema.sql`), task IDs are strings. If initialized via SQLAlchemy `Base.metadata.create_all()`, task IDs are integers.
  * Migrations are executed via unversioned, ad-hoc Python string execution inside `lifespan` without Alembic. If a migration fails midway, the database is left in a corrupted intermediate state with no rollback capability.
* **Remediation:** Establish Alembic as the sole database migration authority, remove ad-hoc startup DDL, and unify Task ID typing across SQL, SQLAlchemy, and TypeScript.

### 3.4. Disaster Recovery & Backup Absence
* **Locations:** [`docker-compose.yml:16, 33`](file:///home/felixsu/koshi/docker-compose.yml#L16)
* **Reality:** The database resides in an unmonitored Docker named volume `koshi-data`. There are no WAL-shipping daemons (e.g., Litestream), no scheduled `sqlite3 .backup` cron tasks, and no off-site S3 snapshot scripts. A filesystem corruption or container destruction will result in **100% unrecoverable data loss**.

---

## 4. PILLAR 3: COMPOUND FRAGILITY & EXTENSION FRICTION

```
+---------------------------------------------------------------------------------------+
| COMPOUND FRAGILITY MATRIX                                                             |
+--------------------------+---------------------+--------------------------------------+
| Subsystem                | Test Coverage       | Architectural Risk                   |
+--------------------------+---------------------+--------------------------------------+
| Frontend Core Stores     | 0% (0 tests)        | Destructive IndexedDB sync clobber   |
| DAG Sorter / TopoSort    | 0% (0 tests)        | Unchecked cycle deadlocks in UI      |
| Backend Routers          | ~15% (6 assertions) | Zero RBAC boundary verification      |
| AI Cascade Fallback      | ~20% (Mock only)    | 14s event-loop blocking timeout      |
| Client-Server ID Bridge  | 0% (Untested)       | Silent background 404 mutations      |
+--------------------------+---------------------+--------------------------------------+
```

### 4.1. Extreme Test Deficit & High Schema Coupling
* **Frontend Test Coverage: 0.00%**
  * [`source_code/frontend/package.json`](file:///home/felixsu/koshi/source_code/frontend/package.json#L6-L10) has no `test` script and no testing libraries installed (no Vitest, Jest, Playwright, or Cypress).
  * Critical algorithmic files ([`dagSorter.ts`](file:///home/felixsu/koshi/source_code/frontend/src/lib/dagSorter.ts), [`gitParser.ts`](file:///home/felixsu/koshi/source_code/frontend/src/lib/gitParser.ts), [`taskStore.ts`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts)) have zero automated unit tests.
* **Backend Test Coverage: ~15%**
  * Only 3 test files exist (`test_auth.py`, `test_tasks.py`, `test_ai_and_stats.py`) with a total of 6 test functions.
  * Zero tests exist for: Multi-tenant RBAC boundaries, cross-project data isolation, concurrent write locks, foreign key cascading, or database transaction rollbacks.
* **Schema Coupling Fragility:** The frontend code is tightly coupled to brittle backend assumptions, using regular expression hacks (`taskId.replace(/\D/g, '')` in [`api.ts:164`](file:///home/felixsu/koshi/source_code/frontend/src/services/api.ts#L164)) to strip non-digit characters from task IDs.

### 4.2. Client-Side State Desynchronization & Silent Data Overwrites
* **Locations:**
  * [`source_code/frontend/src/stores/taskStore.ts:361-395`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L361-L395)
  * [`source_code/frontend/src/stores/taskStore.ts:238-264`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L238-L264)
* **Failure Cascade:**
  1. **Optimistic Task ID Mismatch:** When creating a task offline or locally, `taskStore.createTask()` generates a local ID like `TSK-107` and persists it to IndexedDB. It fires a background `api.createTask()`.
  2. **ID Reconciliation Dropped:** When the backend creates the task in SQLite, it assigns an auto-increment integer ID (e.g., `4`). The frontend **never updates `newTask.id` with the returned backend ID**.
  3. **Silent Update / Delete Failures:** Subsequent calls to `updateTask('TSK-107')` or `deleteTask('TSK-107')` extract numeric ID `107` and issue `PATCH /api/tasks/107`. The backend returns `404 Not Found`, which is caught and silently swallowed by `.catch(() => {})` in `taskStore.ts:409`. The user believes their edits were saved, but the backend state remains unchanged.
  4. **Destructive Reconnection Sync:** When `syncWithBackend()` is called, it unconditionally overwrites `this.tasks = mapped` and calls `persist()`. Any tasks created or modified while offline that failed background synchronization are **permanently wiped out from IndexedDB without conflict resolution or user warning**.

### 4.3. AI Cascade Latency & Resource Exhaustion Failure Modes
* **Location:** [`source_code/backend/app/services/ai_service.py:17-58`](file:///home/felixsu/koshi/source_code/backend/app/services/ai_service.py#L17-L58)
* **Vulnerability Analysis:**
  * In `_call_llm()`, if OpenAI is unresponsive (504/timeout), `httpx.AsyncClient` blocks for **10.0 seconds**.
  * It then falls through to Ollama, which blocks for **4.0 seconds**.
  * Total latency before falling back to deterministic heuristics: **14.0 seconds per request**.
  * Under concurrent user traffic (e.g., multiple users triggering weekly summaries or meeting minute extractions), ASGI worker connection pools and HTTP clients become saturated, causing connection starvation and crashing the backend process.
  * **Static Fallback Data Integrity Risk:** The deterministic fallback for task assignment ([`ai_service.py:99`](file:///home/felixsu/koshi/source_code/backend/app/services/ai_service.py#L99)) hardcodes `"recommended_user_id": 1` ("Phạm Minh Tú"). If User ID 1 is deleted or not part of the project, this introduces invalid foreign key assignment recommendations.

---

## 5. PILLAR 4: INFRASTRUCTURE & RUNTIME ROBUSTNESS

```
+---------------------------------------------------------------------------------------+
| INFRASTRUCTURE & RUNTIME AUDIT                                                        |
+--------------------------+---------------------+--------------------------------------+
| Subsystem                | Configuration State | Operational Hazard                   |
+--------------------------+---------------------+--------------------------------------+
| Nginx Reverse Proxy      | Default configs     | No rate limits, no body size caps    |
| Container Limits         | None (Unbounded)    | Host OS OOM Kill under load          |
| Logging / Telemetry      | Raw `print()`       | No JSON logs, zero correlation IDs   |
| Health Checks            | Unmonitored         | No container restart on freeze       |
+--------------------------+---------------------+--------------------------------------+
```

### 5.1. Reverse Proxy Deficiencies & Missing Protections
* **Location:** [`source_code/frontend/nginx.conf`](file:///home/felixsu/koshi/source_code/frontend/nginx.conf)
* **Deficiencies:**
  1. **No `client_max_body_size`:** Missing explicit body limits. Large diffs, meeting transcripts, or malicious file payloads can overwhelm worker memory.
  2. **No Rate Limiting:** Missing `limit_req_zone` / `limit_req`. The backend endpoints (`/api/auth/login`, `/api/ai/*`) are vulnerable to brute-force credential stuffing and upstream API cost exhaustion.
  3. **No Proxy Timeouts for Long-Running Requests:** Default proxy timeout (60s) is unaligned with AI streaming or batch operations.
  4. **Permissive CSP:** Missing strict `Content-Security-Policy` header.

### 5.2. Unbounded Container Resource Allocation (OOM Killer Hazard)
* **Location:** [`docker-compose.yml:1-31`](file:///home/felixsu/koshi/docker-compose.yml#L1-L31)
* **Vulnerability:** Neither `koshi-backend` nor `koshi-frontend` defines `deploy.resources.limits` (CPU / Memory limits).
* **Impact:** If an unoptimized AST parsing loop, complex DAG cycle traversal, or memory leak occurs in Python, the container will consume all host memory, triggering the Linux kernel Out-Of-Memory (OOM) killer to terminate host-level services.

### 5.3. Telemetry, Observability & Structured Logging Vacuum
* **Locations:** Throughout `source_code/backend/app/`
* **Vulnerability:**
  * Logging is implemented via raw `print()` statements (e.g., [`main.py:163`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L163): `print("Migration notice:", e)`).
  * No structured JSON logging format (e.g., Structlog / Loguru).
  * No request correlation ID middleware (`X-Request-ID`), preventing request tracing across reverse proxy and backend.
  * No Prometheus metrics exporter, OpenTelemetry instrumentation, or Sentry error tracking. System failures in production will occur completely unmonitored.

---

## 6. PILLAR 5: 18-MONTH TCO & REMEDIATION ROADMAP

### 6.1. Executive Risk Matrix

| Risk Item | Severity | Impact Area | Remediation Effort (Hours) |
| :--- | :--- | :--- | :--- |
| **Google OAuth Signature Bypass** | **DEAL-KILLER** | Security & Auth | 16 hrs |
| **Hardcoded JWT Secret & Seed Passwords** | **DEAL-KILLER** | Security & Config | 8 hrs |
| **Total Absence of RBAC / Tenant Isolation** | **DEAL-KILLER** | Data Security & Multi-Tenancy | 80 hrs |
| **SQLite Concurrency Locks & Missing WAL** | **DEAL-KILLER** | Database Stability | 24 hrs |
| **Disabled SQLite Foreign Key Enforcement** | **HIGH** | Data Integrity | 16 hrs |
| **Client-Server State Desync & Silent Data Loss** | **DEAL-KILLER** | Core Frontend / API | 60 hrs |
| **Alembic Migration System Implementation** | **HIGH** | Architecture & Database | 30 hrs |
| **PostgreSQL Migration (Replace SQLite)** | **HIGH** | Scalability & Concurrency | 50 hrs |
| **Frontend Test Suite (Vitest + Store Unit Tests)** | **HIGH** | Code Quality & Reliability | 40 hrs |
| **Backend Integration & Concurrency Test Suite** | **HIGH** | Testing & Stability | 36 hrs |
| **Structured JSON Logging & Correlation IDs** | **MEDIUM** | Observability | 16 hrs |
| **Automated Backups & Disaster Recovery (Litestream/S3)** | **HIGH** | Infrastructure & DR | 20 hrs |
| **Docker Resource Constraints & Nginx Hardening** | **MEDIUM** | Deployment & Security | 14 hrs |
| **Total Initial Remediation Effort** | | | **410 Hours** |

---

### 6.2. 18-Month Maintenance & Extension Cost Projection

```
+---------------------------------------------------------------------------------------+
| 18-MONTH TOTAL COST OF OWNERSHIP (TCO) PROJECTION                                     |
+------------------------------------+------------------+-------------------------------+
| Phase / Activity                   | Timeline         | Required Engineering Hours    |
+------------------------------------+------------------+-------------------------------+
| Phase 1: Security & Triage Hotfixes| Month 1          | 120 Hours                     |
| Phase 2: PostgreSQL & Sync Rewrite | Month 2 - 3      | 290 Hours                     |
| Phase 3: Test Automation & CI/CD   | Month 4 - 6      | 210 Hours                     |
| Phase 4: Ongoing Maintenance & Ops | Month 7 - 18     | 660 Hours (55 hrs/month)      |
+------------------------------------+------------------+-------------------------------+
| TOTAL 18-MONTH ENGINEERING BURDEN  | 18 Months        | 1,280 Hours                   |
+------------------------------------+------------------+-------------------------------+
```

#### Detailed Breakdown of Operational Expenses:
1. **Security & State Triage (Month 1 - 120 hrs):**
   * Eliminate OAuth signature bypass and enforce secure JWT rotation.
   * Patch BOLA/IDOR vulnerabilities across all routers with project-membership middleware.
   * Configure SQLite WAL mode and busy timeouts as temporary stopgap.
2. **Data Layer Re-Architecture & Sync Rewrite (Month 2–3 - 290 hrs):**
   * Migrate storage engine from SQLite to PostgreSQL with connection pooling (AsyncPG/SQLAlchemy).
   * Implement Alembic version-controlled migrations.
   * Completely rewrite `taskStore.ts` and `api.ts` state synchronization to implement optimistic ID mapping, a client-side mutation queue, and conflict-resolution strategies.
3. **Quality Engineering & CI/CD Pipeline (Month 4–6 - 210 hrs):**
   * Implement Vitest for frontend with unit tests for `taskStore`, `dagSorter`, and `gitParser`.
   * Implement Pytest suite covering all RBAC boundaries, concurrency scenarios, and AI fallbacks.
   * Establish GitHub Actions CI/CD with automated linting, security scanning (Trivy), and test validation.
4. **Routine Maintenance, Upgrades & Incident Response (Month 7–18 - 660 hrs):**
   * Dependency lifecycle management and security patches (~15 hrs/month).
   * Infrastructure telemetry, backup verification, and database vacuum/indexing (~15 hrs/month).
   * Operational bug fixes, AI token cost optimization, and tenant support (~25 hrs/month).

---

### 6.3. Concluding Assessment
The Koshi repository demonstrates functional UI prototyping and algorithmic concept modeling (topological sorting, keyboard traversal), but **lacks fundamental production engineering controls**. The presence of remote authentication bypasses, hardcoded secrets, unchecked cross-tenant access, and destructive data synchronization make it completely unsuitable for multi-tenant production deployment without executing the full 410-hour remediation roadmap detailed above.
