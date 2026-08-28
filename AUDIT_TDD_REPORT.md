# TECHNICAL DUE DILIGENCE (TDD) & PRINCIPAL SYSTEMS AUDIT REPORT

**Target Codebase:** `~/koshi` (`source_code/backend/`, `source_code/frontend/`, Root Deployment Manifests)  
**Stack:** Vue 3.5 (TypeScript / Pinia) + FastAPI (Python 3.11 / SQLite / SQLAlchemy 2.0) + Nginx / Docker Compose  
**Audit Scope:** 18-Month Operational Horizon, Multi-Tenant Viability & Failure Risk Assessment  
**Auditor:** Principal Systems Auditor & TDD Assessor  
**Date:** 2026-08-28  

---

## EXECUTIVE SUMMARY & PRODUCTION DEPLOYMENT VERDICT

### Production Deployment Verdict: **CONDITIONAL GO (Single-Tenant / Staging Only) | NO-GO (Multi-Tenant SaaS / Enterprise)**

```
+---------------------------------------------------------------------------------------------------+
| TDD RISK PROFILE SUMMARY                                                                          |
+------------------------------+--------------------+-----------------------------------------------+
| Category                     | Severity           | Core Risk / Bottleneck                        |
+------------------------------+--------------------+-----------------------------------------------+
| Secrets & Fallbacks          | High Risk (P1)     | Hardcoded JWT secret fallback in Compose manifest|
| Multi-Tenancy & RBAC         | High Risk (P1)     | Global user enumeration & global PM role leak |
| Concurrency & Storage        | High Risk (P1)     | SQLite serialized single-writer lock risk     |
| Disaster Recovery / Backup   | Deal-Killer (P0)   | 0 automated volume snapshots / backup scripts |
| Offline State Sync           | High Risk (P1)     | Zombie tasks & missing offline outbox queue   |
| Test Coverage & CI/CD        | High Risk (P1)     | 0 frontend tests; 7 backend tests total       |
| Observability & Logging      | Medium Risk (P2)   | Raw console logs; 0 structured JSON / req IDs |
+------------------------------+--------------------+-----------------------------------------------+
```

---

## PILLAR 1: DEAL-KILLER TRIAGE & SECURITY POSTURE

### 1.1. Secrets & Credentials Vulnerabilities

#### [VULN-01] Hardcoded JWT Fallback Secret in Production Deployment Manifest
- **File:** [`docker-compose.yml:10`](file:///home/felixsu/koshi/docker-compose.yml#L10)
- **Code:**
  ```yaml
  - JWT_SECRET=${JWT_SECRET:-d9a83f4b1e5c2a7f8093e614b82d3f7a1c9e8b0d4f2a6e3c5b8a1f7d9e2c4b6a}
  ```
- **Analysis:**
  - `docker-compose.yml` provides a static, committed 64-character hex fallback for `JWT_SECRET`.
  - While [`app/config.py:48-54`](file:///home/felixsu/koshi/source_code/backend/app/config.py#L48-L54) validates and rejects the academic placeholder string (`koshi_super_secret_jwt_key_2026_academic_spec`), it permits the 64-character compose fallback without error.
  - Any deployment executed without explicitly defining `JWT_SECRET` in the host `.env` runs with a publicly exposed cryptographic key. An external adversary can forge valid HS256 tokens with arbitrary claims (`{"sub": "1", "role": "PM"}`).
- **Remediation:** Remove fallback value from `docker-compose.yml`. Enforce mandatory non-empty environment variable requirement at container startup.
- **Effort:** 1 hour.

---

### 1.2. Authentication, RBAC & Multi-Tenant Boundaries

#### [VULN-02] Global User Directory Enumeration & Tenant Information Leak
- **File:** [`source_code/backend/app/routers/users.py:24-54`](file:///home/felixsu/koshi/source_code/backend/app/routers/users.py#L24-L54), [`source_code/backend/app/routers/users.py:11-22`](file:///home/felixsu/koshi/source_code/backend/app/routers/users.py#L11-L22)
- **Code:**
  ```python
  @router.get("", response_model=List[UserWithWIPOut])
  def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
      users = db.query(User).order_by(User.id.asc()).all()
  ```
- **Analysis:**
  - `GET /api/users` and `GET /api/users/search` require authentication but lack project/organization isolation.
  - Any authenticated user in Tenant A can query and retrieve every user record in the system across all tenants, including full names, emails, avatar URLs, skills, active task counts, and workload complexity points.
- **Remediation:** Scope user queries to projects shared with `current_user` or implement explicit Organization/Tenant entities.
- **Effort:** 6 hours.

#### [VULN-03] Global PM Role Privilege Escalation Across Tenants
- **File:** [`source_code/backend/app/routers/users.py:56-80`](file:///home/felixsu/koshi/source_code/backend/app/routers/users.py#L56-L80)
- **Code:**
  ```python
  @router.patch("/{user_id}", response_model=UserOut)
  def update_user_profile(
      user_id: int,
      payload: UserUpdate,
      db: Session = Depends(get_db),
      current_user: User = Depends(require_role(RoleEnum.PM))
  ):
  ```
- **Analysis:**
  - `PATCH /api/users/{user_id}` uses `require_role(RoleEnum.PM)` from [`app/security.py:71-79`](file:///home/felixsu/koshi/source_code/backend/app/security.py#L71-L79).
  - `RoleEnum.PM` is stored on the global `users` table, not scoped to individual projects.
  - Any user with PM privileges can mutate any other user's name, skills, or global role across the entire system.
- **Remediation:** Remove global `User.role` mutability via general endpoints; restrict role modifications to project-level roles (`ProjectMember.role`) governed by `ProjectMemberRoleEnum.OWNER`.
- **Effort:** 8 hours.

#### [VULN-04] Long-Lived Stateless Tokens with Zero Revocation Capability
- **File:** [`source_code/backend/app/config.py:22`](file:///home/felixsu/koshi/source_code/backend/app/config.py#L22), [`source_code/backend/app/security.py:28-36`](file:///home/felixsu/koshi/source_code/backend/app/security.py#L28-L36)
- **Analysis:**
  - Token validity is configured to 7 days (`ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080`).
  - System uses purely stateless JWT verification without a token blacklist, revocation cache (Redis), or user token-version salt.
  - If a JWT is compromised or a user is removed from a team, the token remains valid for up to 7 days.
- **Remediation:** Shorten access token lifetime to 15-30 minutes, implement refresh token rotation with database/Redis revocation tracking.
- **Effort:** 12 hours.

---

### 1.3. Single-Person Bus Factor & Operational Reproducibility

#### [RISK-01] Missing Database Migration Framework (No Alembic)
- **File:** [`source_code/backend/app/main.py:140-164`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L140-L164), [`source_code/backend/requirements.txt`](file:///home/felixsu/koshi/source_code/backend/requirements.txt)
- **Analysis:**
  - Migrations are executed via raw string SQL inside `migrate_database()` during FastAPI startup.
  - Alembic is missing from `requirements.txt`.
  - Schema changes cannot be rolled back, versioned, or tracked across branching workflows.
- **Remediation:** Initialize Alembic, generate base revision from SQLAlchemy models, eliminate raw SQL startup hooks.
- **Effort:** 10 hours.

---

## PILLAR 2: DATA INTEGRITY & DATABASE FAILURE MODES

### 2.1. SQLite Concurrency & Write-Lock Contention

```
+---------------------------------------------------------------------------------------------------+
| SQLITE WRITE-LOCK BOTTLENECK ANALYSIS                                                             |
+-------------------------+-------------------------+-----------------------------------------------+
| Parameter               | Configuration           | Concurrency Impact                            |
+-------------------------+-------------------------+-----------------------------------------------+
| Journal Mode            | WAL (`journal_mode=WAL`)| Concurrent readers permitted; 1 writer max    |
| Busy Timeout            | 30,000 ms               | Blocked worker threads hold connections       |
| Synchronous Flag        | NORMAL                  | Fast WAL write; crash safe on OS flush        |
| Connection Pooling      | SQLAlchemy Default      | QueuePool unthrottled against single DB lock  |
+-------------------------+-------------------------+-----------------------------------------------+
```

#### [RISK-02] SQLite Single-Writer Serialized Bottleneck Under Concurrent Load
- **File:** [`source_code/backend/app/database.py:13-30`](file:///home/felixsu/koshi/source_code/backend/app/database.py#L13-L30)
- **Analysis:**
  - WAL mode and 30-second `busy_timeout` are configured via SQLAlchemy connection listener.
  - SQLite enforces serialized single-writer locking. When multiple users submit concurrent write requests (e.g. batch task creation, status cycles, AI subtask decomposition), write operations block waiting for lock release.
  - If a write transaction stalls or lock contention exceeds 30 seconds, SQLite raises `OperationalError: database is locked`, returning HTTP 500/504 to clients.
- **Remediation:** Retain SQLite for development/testing only; migrate production engine to PostgreSQL for multi-user / multi-tenant deployments.
- **Effort:** 24 hours (PostgreSQL migration + schema testing).

---

### 2.2. Referential Integrity & Dependency Storage

#### [RISK-03] Denormalized JSON Dependency Storage Bypasses SQLite Foreign Key Cascades
- **File:** [`source_code/backend/app/models/entities.py:101-120`](file:///home/felixsu/koshi/source_code/backend/app/models/entities.py#L101-L120), [`source_code/backend/app/routers/tasks.py:108-116`](file:///home/felixsu/koshi/source_code/backend/app/routers/tasks.py#L108-L116)
- **Analysis:**
  - `task_dependencies` relational table is defined in [`entities.py:144-152`](file:///home/felixsu/koshi/source_code/backend/app/models/entities.py#L144-L152) but unused by application routes.
  - Routes store dependency IDs as JSON strings inside `tasks.dependencies_json`.
  - SQLite engine-level `PRAGMA foreign_keys = ON;` cannot validate or cascade updates inside JSON blobs. Deleting a task via direct SQL or external script leaves dangling ID references in sibling task JSON arrays.
- **Remediation:** Migrate `dependencies_json` to relational `task_dependencies` table with active foreign keys.
- **Effort:** 14 hours.

---

### 2.3. Disaster Recovery & Backup Plan

#### [DEAL-KILLER-01] Zero Automated Backup / Snapshot Pipeline for Persistent Volume
- **File:** [`docker-compose.yml:59-61`](file:///home/felixsu/koshi/docker-compose.yml#L59-L61)
- **Analysis:**
  - Database file `/app/data/koshi.db` resides on an unbacked Docker named volume (`koshi-data`).
  - No automated Litestream streaming, cron snapshot, S3 backup, or volume dump mechanism exists in the codebase.
  - A single host storage failure, corrupted WAL file, or inadvertent volume deletion causes complete, irrecoverable data loss (RPO = $\infty$).
- **Remediation:** Deploy Litestream sidecar container targeting S3/GCS bucket for real-time WAL replication, or configure hourly automated SQLite vacuum backups.
- **Effort:** 16 hours.

---

## PILLAR 3: COMPOUND FRAGILITY & EXTENSION FRICTION

### 3.1. Test Coverage vs. Architectural Coupling

```
+---------------------------------------------------------------------------------------------------+
| TEST COVERAGE AUDIT MATRIX                                                                        |
+----------------------+--------------------+-------------------+-----------------------------------+
| Component Layer      | Total Files        | Automated Tests   | Coverage Status                   |
+----------------------+--------------------+-------------------+-----------------------------------+
| Backend Routers      | 7 router modules   | 7 test functions  | Minimal (~30% endpoint coverage)  |
| Backend AI / Stats   | 2 service modules  | 2 test functions  | Heuristics tested; 0 LLM mocks    |
| Frontend Core Stores | `taskStore.ts`     | 0 tests           | 0% Coverage                       |
| Frontend Algorithms  | `dagSorter.ts`     | 0 tests           | 0% Coverage                       |
| Frontend Components  | 16 Vue components  | 0 tests           | 0% Coverage                       |
+----------------------+--------------------+-------------------+-----------------------------------+
```

#### [RISK-04] Zero Automated Frontend Test Suite & Fragile Schema Mapping
- **File:** [`source_code/frontend/package.json:6-10`](file:///home/felixsu/koshi/source_code/frontend/package.json#L6-L10), [`source_code/frontend/src/stores/taskStore.ts:303-316`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L303-L316)
- **Analysis:**
  - `package.json` contains no test runner (Vitest, Jest, or Playwright).
  - Critical client-side algorithms (`topologicalSort`, `computeCriticalPath` in [`dagSorter.ts`](file:///home/felixsu/koshi/source_code/frontend/src/lib/dagSorter.ts)) operate without unit test validation.
  - `taskStore.ts` manually converts backend snake_case properties (`complexity_points: 1|2|3|5`) to client camelCase types (`complexity: 'S'|'M'|'L'|'XL'`). Any schema divergence triggers silent runtime UI rendering bugs.
- **Remediation:** Install Vitest + Vue Test Utils; add unit tests for `dagSorter.ts`, `taskStore.ts`, and optimistic sync routines.
- **Effort:** 28 hours.

---

### 3.2. AI Cascade Architecture & Latency Cascades

#### [RISK-05] Upstream LLM Latency Cascades Block Client Requests
- **File:** [`source_code/backend/app/services/ai_service.py:16-59`](file:///home/felixsu/koshi/source_code/backend/app/services/ai_service.py#L16-L59)
- **Analysis:**
  - Cascade order: OpenAI API (10s timeout) $\rightarrow$ Ollama Local (4s timeout) $\rightarrow$ Deterministic Heuristic Engine.
  - In an outage scenario where external AI APIs hang or rate-limit (HTTP 429/504), a single request will block for up to 14 seconds before triggering the fallback.
  - Multiple concurrent AI requests will saturate ASGI worker concurrency, degrading backend responsiveness.
- **Remediation:** Implement circuit breaker pattern (e.g. `pybreaker`) with fast-fail thresholds and background asynchronous task queues (Celery/ARQ).
- **Effort:** 16 hours.

---

### 3.3. Client-Side State Desynchronization (Optimistic Offline vs REST)

#### [RISK-06] Zombie Task Resurrections & Missing Offline Outbox Queue
- **File:** [`source_code/frontend/src/stores/taskStore.ts:299-340`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L299-L340), [`source_code/frontend/src/stores/taskStore.ts:500-530`](file:///home/felixsu/koshi/source_code/frontend/src/stores/taskStore.ts#L500-L530)
- **Analysis:**
  - **Offline Task Creation:** `createTask` generates `TSK-temp-*`. If offline, `syncWithBackend` keeps `TSK-temp-*` locally but never replays the creation payload to the server upon reconnection (missing outbox queue).
  - **Offline Task Deletion (Zombie Tasks):** `deleteTask` removes the task locally and fires `api.deleteTask().catch(() => {})`. If network fails, the deletion is not recorded on backend. When `syncWithBackend` executes later, the server returns the non-deleted task, resurrecting it in the UI.
  - **Conflict Resolution:** Store relies on client wall-clock timestamps (`local.updatedAt > sTask.updatedAt`), exposing data to silent overwrite via client clock drift.
- **Remediation:** Implement explicit IndexedDB mutation outbox queue with sequence IDs and vector clocks / server revision counters.
- **Effort:** 32 hours.

---

## PILLAR 4: INFRASTRUCTURE & RUNTIME ROBUSTNESS

### 4.1. Reverse Proxy & Network Configuration

```
+---------------------------------------------------------------------------------------------------+
| INFRASTRUCTURE HARDENING AUDIT                                                                    |
+--------------------------+-----------------------+------------------------------------------------+
| Area                     | Status                | Finding / Gap                                  |
+--------------------------+-----------------------+------------------------------------------------+
| Static Asset Compression | Configured (PASS)     | Gzip enabled on CSS/JS/HTML in `nginx.conf`    |
| Security Headers         | Configured (PASS)     | X-Frame-Options, X-Content-Type, X-XSS present |
| Request Body Size Limits | Absent (RISK)         | Missing `client_max_body_size` directive       |
| API Rate Limiting        | Absent (RISK)         | No `limit_req_zone` configured in Nginx        |
| Resource Limits (Docker) | Configured (PASS)     | Backend: 2 CPU / 1GB RAM; Frontend: 1 CPU/512M |
+--------------------------+-----------------------+------------------------------------------------+
```

#### [RISK-07] Missing Nginx Rate Limiting and Body Limits
- **File:** [`source_code/frontend/nginx.conf:21-28`](file:///home/felixsu/koshi/source_code/frontend/nginx.conf#L21-L28)
- **Analysis:**
  - Nginx configuration lacks rate limiting on `/api/` endpoints.
  - No custom `client_max_body_size` is specified.
- **Remediation:** Add `limit_req_zone` for auth and AI endpoints; specify `client_max_body_size 10M;`.
- **Effort:** 3 hours.

---

### 4.2. Telemetry, Logging & Observability

#### [RISK-08] Unstructured Console Logging & Zero Request Correlation Tracing
- **File:** [`source_code/backend/app/main.py:162-164`](file:///home/felixsu/koshi/source_code/backend/app/main.py#L162-L164), [`source_code/backend/app/services/ai_service.py:33-35`](file:///home/felixsu/koshi/source_code/backend/app/services/ai_service.py#L33-L35)
- **Analysis:**
  - System uses raw Python `print()` statements and standard Uvicorn log output.
  - Errors inside AI service are silently swallowed (`pass`) without log traces.
  - No correlation ID middleware (`X-Request-ID`), structured JSON logging, or APM instrumentation exists.
- **Remediation:** Implement structured JSON logging middleware with correlation IDs and OpenTelemetry instrumentation.
- **Effort:** 12 hours.

---

## PILLAR 5: 18-MONTH TCO & REMEDIATION ROADMAP

### 5.1. Executive Risk Matrix

```
| Risk ID | Risk Description | Severity | Impact Area | Remediation Effort |
|---|---|---|---|---|
| DEAL-KILLER-01 | Missing Automated Backup / Disaster Recovery | Deal-Killer (P0) | Storage / Ops | 16 Hours |
| VULN-01 | Hardcoded Fallback JWT Secret in Compose Manifest | High (P1) | Security | 1 Hour |
| VULN-02 | Global User Directory Enumeration Across Tenants | High (P1) | Multi-Tenancy | 6 Hours |
| VULN-03 | Global PM Privilege Escalation Across Tenants | High (P1) | RBAC | 8 Hours |
| VULN-04 | 7-Day Stateless JWT Tokens Without Revocation List | High (P1) | Auth | 12 Hours |
| RISK-01 | Missing Database Migration Framework (No Alembic) | High (P1) | Database Ops | 10 Hours |
| RISK-02 | SQLite Single-Writer Lock Contention Under Concurrency | High (P1) | Database Engine | 24 Hours |
| RISK-03 | Denormalized JSON Dependency Storage Bypasses Cascades | High (P1) | Data Integrity | 14 Hours |
| RISK-04 | Zero Frontend Automated Tests & Schema Coupling | High (P1) | Quality / CI | 28 Hours |
| RISK-05 | Upstream LLM Latency Cascades Without Circuit Breakers | High (P1) | AI Reliability | 16 Hours |
| RISK-06 | Offline State Desynchronization & Zombie Tasks | High (P1) | Frontend Store | 32 Hours |
| RISK-07 | Missing Nginx Rate Limiting & Body Size Directives | Medium (P2) | Edge Security | 3 Hours |
| RISK-08 | Unstructured Logging & Swallowed AI Exceptions | Medium (P2) | Observability | 12 Hours |
| TOTAL | Core Hardening & Remediation Package | | | 182 Hours |
```

---

### 5.2. 18-Month Total Cost of Ownership (TCO) Projection

```
+---------------------------------------------------------------------------------------------------+
| 18-MONTH ENGINEERING MAINTENANCE & SCALING EFFORT PROJECTION                                     |
+---------------------------------------------------------------------------+-----------------------+
| Operational Phase / Workstream                                            | Projected Effort      |
+---------------------------------------------------------------------------+-----------------------+
| Phase 1: Immediate P0/P1 Security & Backup Remediation (Months 1-2)       | 50 Hours              |
| Phase 2: PostgreSQL Engine Migration & Relational Normalization (Months 3-4)| 60 Hours             |
| Phase 3: Offline Outbox Queue & Real-Time Sync Engine (Months 5-6)         | 70 Hours              |
| Phase 4: Frontend Vitest/Playwright Test Suite & CI/CD Pipeline (Month 6)  | 50 Hours              |
| Phase 5: Ongoing Security Patches, Upgrades & Dependency Upkeep (18 Mos)  | 90 Hours              |
| Phase 6: Operational Incidents, SQLite Contention Debugging & On-Call     | 60 Hours              |
+---------------------------------------------------------------------------+-----------------------+
| TOTAL 18-MONTH TCO BURDEN                                                 | 380 Engineering Hours |
+---------------------------------------------------------------------------+-----------------------+
```

---

### 5.3. Final Go / No-Go Verdict Summary

- **Production Multi-Tenant SaaS Deployment:** **NO-GO.** The system currently lacks tenant-isolated user directories, token revocation mechanisms, transactional database replication, and an offline mutation queue.
- **Internal Single-Team Staging Deployment:** **CONDITIONAL GO.** Viable for single-team internal evaluation provided that:
  1. `JWT_SECRET` is explicitly injected via host environment.
  2. An external backup cron script snapshots `/app/data/koshi.db` hourly.
  3. Concurrent write users remain below 15 developers.
